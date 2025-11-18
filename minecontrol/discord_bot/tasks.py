import asyncio
import re
import subprocess
import time
from typing import cast

import discord
from discord.ext import commands, tasks

from minecontrol.config import MinecraftConfig
from minecontrol.discord_bot.commands import get_minecraft_server_status
from minecontrol.discord_bot.guild_config import GuildConfigManager
from minecontrol.rcon_client import RCONConnectionError, SimpleRCONClient

from .enums import AutoShutdownStatus, ServerStatus
from .utils import send_announcement


class AutoShutdownState:
    def __init__(self):
        self.status: AutoShutdownStatus = AutoShutdownStatus.MONITORING
        self.empty_start_time: float | None = None
        self.shutdown_countdown_start_time: float | None = None

    def reset(self):
        """Resetea el estado a su valor por defecto."""
        self.status = AutoShutdownStatus.MONITORING
        self.empty_start_time = None
        self.shutdown_countdown_start_time = None


shutdown_state = AutoShutdownState()


async def get_player_count(config: MinecraftConfig) -> int:
    """Obtiene el número de jugadores conectados vía RCON."""
    try:
        async with SimpleRCONClient(
            config.rcon_host, config.rcon_port, config.rcon_password
        ) as client:
            response = await client.execute("list")

            print(f"DEBUG: Respuesta RCON del comando 'list': '{response}'")
            match = re.search(r"(\d+)/\d+|There are (\d+) of", response)

            if match:
                # El grupo 1 de la expresión regular es el primer número (los jugadores actuales).
                player_count_str = match.group(1) or match.group(2)
                return int(player_count_str)
            else:
                # Si no se encuentra el patrón, asumimos que hubo un error y devolvemos -1
                print(
                    f"WARN: No se pudo extraer el contador de jugadores de la respuesta RCON: '{response}'"
                )
                return -1
    except (RCONConnectionError, asyncio.TimeoutError):
        return -1
    except Exception:
        return -1


@tasks.loop(minutes=1.0)
async def auto_shutdown_loop(
    bot: commands.Bot,
    mc_config: MinecraftConfig,
    guild_manager: GuildConfigManager,
    guild_id: int,
):
    is_online = await get_minecraft_server_status(mc_config) == ServerStatus.ONLINE
    if not is_online:
        shutdown_state.reset()
        return

    player_count = await get_player_count(mc_config)
    if player_count == -1:
        print("Auto-Shutdown: No se pudo conectar a RCON. Se omite el ciclo.")
        return

    print(f"Auto-Shutdown: Jugadores conectados: {player_count}")

    # CASO 1: Hay jugadores. Volvemos al estado de monitoreo.
    if player_count > 0:
        if shutdown_state.status != AutoShutdownStatus.MONITORING:
            # avisamos que se cancela el apagado
            print(
                "Auto-Shutdown: Jugador detectado. Se cancela el apagado y se vuelve a monitorear."
            )
        shutdown_state.reset()
        return

    # CASO 2: No hay jugadores. Actuamos según el estado actual.

    # Si estábamos monitoreando, ahora empezamos a cronometrar.
    if shutdown_state.status == AutoShutdownStatus.MONITORING:
        print(f"Auto-Shutdown: Servidor vacío. Transición a TIMING_EMPTY.")
        shutdown_state.status = AutoShutdownStatus.TIMING_EMPTY
        shutdown_state.empty_start_time = time.time()
        return

    # Si ya estábamos cronometrando, vemos si se acabó el tiempo.
    elif shutdown_state.status == AutoShutdownStatus.TIMING_EMPTY:
        idle_duration = time.time() - cast(float, shutdown_state.empty_start_time)
        if idle_duration >= mc_config.auto_shutdown_idle_minutes * 60:
            print(
                f"Auto-Shutdown: Tiempo de inactividad superado. Transición a SHUTDOWN_COUNTDOWN."
            )
            shutdown_state.status = AutoShutdownStatus.SHUTDOWN_COUNTDOWN
            shutdown_state.shutdown_countdown_start_time = time.time()

        return

    # Si ya estábamos en la cuenta atrás, vemos si llegó a cero.
    elif shutdown_state.status == AutoShutdownStatus.SHUTDOWN_COUNTDOWN:
        countdown_duration = time.time() - cast(
            float, shutdown_state.shutdown_countdown_start_time
        )
        if countdown_duration >= mc_config.auto_shutdown_countdown_seconds:
            print("Auto-Shutdown: Cuenta atrás finalizada. Ejecutando apagado.")
            try:
                subprocess.run(
                    [
                        "tmux",
                        "send-keys",
                        "-t",
                        mc_config.terminal_session_name,
                        "stop",
                        "C-m",
                    ],
                    check=True,
                )

                await asyncio.sleep(5)
                await send_announcement(
                    bot=bot,
                    guild_manager=guild_manager,
                    guild_id=guild_id,
                    title="Servidor Apagado por Inactividad",
                    description=f"El servidor se ha apagado automáticamente después de estar vacío por más de {mc_config.auto_shutdown_idle_minutes} minutos.",
                    color=discord.Color.orange(),
                    footer_text="Se iniciará de nuevo cuando alguien use /server_start.",
                )

            except subprocess.CalledProcessError as e:
                print(f"Error al ejecutar el comando de apagado por tmux: {e}")
            finally:
                shutdown_state.reset()
        return
