import asyncio
import random
import socket
import struct


class RCONConnectionError(Exception):
    """No se pudo conectar al servidor RCON."""

    pass


class RCONAuthError(Exception):
    """La autenticación RCON falló (contraseña incorrecta)."""

    pass


# Entendiendo el Protocolo RCON
# Un paquete RCON es una estructura de bytes simple. Se ve así:
# Longitud (4 bytes) | ID de Petición (4 bytes) | Tipo (4 bytes) | Payload (N bytes) | Terminador (2 bytes)
# Longitud: Un entero de 32 bits que indica el tamaño del resto del paquete (ID + Tipo + Payload + Terminador).
# ID de Petición: Un número que tú eliges. El servidor te responderá usando el mismo ID, para que puedas asociar respuestas con peticiones.
# Tipo: Un entero que define el propósito del paquete. Los más importantes son:
# 3: SERVERDATA_AUTH (para iniciar sesión con la contraseña).
# 2: SERVERDATA_EXECCOMMAND (para enviar un comando).
# 0: SERVERDATA_RESPONSE_VALUE (la respuesta del servidor a un comando).
# 2: SERVERDATA_AUTH_RESPONSE (la respuesta del servidor a la autenticación).
# Payload: Los datos en sí (la contraseña o el comando), codificados en ASCII.
# Terminador: Dos bytes nulos (\x00\x00) para marcar el final.
# Para comunicarse, envías un paquete al servidor y luego lees su respuesta, que sigue el mismo formato.


class SimpleRCONClient:
    """Un cliente RCON asíncrono y minimalista para Minecraft."""

    def __init__(self, host: str, port: int, password: str, timeout: int = 5):
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self._reader = None
        self._writer = None

    async def __aenter__(self):
        """Permite el uso con 'async with'."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cierra la conexión al salir del bloque 'async with'."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

    def _create_packet(self, req_id: int, req_type: int, payload: str) -> bytes:
        """Construye un paquete RCON en el formato de bytes correcto."""
        payload_bytes = payload.encode("ascii")
        # Formato: < (little-endian), i (entero de 4 bytes)
        # Paquete: ID, Tipo, Payload, Terminador (2 bytes nulos)
        packet_data = struct.pack("<ii", req_id, req_type) + payload_bytes + b"\x00\x00"
        # Longitud total del paquete (sin incluir el campo de longitud en sí)
        packet_len = len(packet_data)
        # Paquete final con la longitud al principio
        return struct.pack("<i", packet_len) + packet_data

    async def _read_response(self) -> tuple[int, str]:
        """Lee y decodifica una respuesta del servidor."""
        # Lee los primeros 4 bytes para obtener la longitud del paquete
        len_data = await asyncio.wait_for(self._reader.readexactly(4), self.timeout)  # type: ignore
        packet_len = struct.unpack("<i", len_data)[0]

        # Lee el resto del paquete
        packet_data = await asyncio.wait_for(
            self._reader.readexactly(packet_len), self.timeout  # type: ignore
        )

        # Desempaqueta el ID y el Tipo
        req_id, res_type = struct.unpack("<ii", packet_data[:8])

        # El payload es el resto, menos los 2 bytes nulos del final
        payload = packet_data[8:-2].decode("ascii", errors="ignore")

        return res_type, payload

    async def connect(self):
        """Establece la conexión y se autentica."""
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), self.timeout
            )
        except (asyncio.TimeoutError, ConnectionRefusedError, socket.gaierror) as e:
            raise RCONConnectionError(
                f"No se pudo conectar a {self.host}:{self.port}: {e}"
            )

        await self._authenticate()

    async def _authenticate(self):
        """Envía el paquete de autenticación."""
        auth_id = random.randint(0, 2**31 - 1)
        auth_packet = self._create_packet(auth_id, 3, self.password)
        self._writer.write(auth_packet)  # type: ignore
        await self._writer.drain()  # type: ignore

        # Minecraft responde con un paquete de tipo 2 (SERVERDATA_AUTH_RESPONSE)
        # y un ID de -1 si la autenticación falla.
        res_type, _ = await self._read_response()
        if res_type != 2:  # No es una respuesta de autenticación
            raise RCONAuthError(
                "El servidor no respondió correctamente a la autenticación."
            )

    async def execute(self, command: str) -> str:
        """Ejecuta un comando y devuelve la respuesta."""
        if not self._writer:
            raise RCONConnectionError(
                "No conectado. Llama a connect() primero o usa 'async with'."
            )

        cmd_id = random.randint(0, 2**31 - 1)
        cmd_packet = self._create_packet(cmd_id, 2, command)
        self._writer.write(cmd_packet)
        await self._writer.drain()

        res_type, payload = await self._read_response()

        # Nota: Algunos comandos (como 'list') pueden enviar una respuesta vacía primero.
        return payload
