🚧🔨👷‍♂️

    ⚠️ AVISO: Proyecto en Fase Inicial ⚠️
    
    MineControl se encuentra en sus primeras etapas de desarrollo. 
    Aunque es un proyecto seguro, es posible que hayan funcionalidades incompletas, 
    errores menores o comportamientos inesperados.


# MineControl

**MineControl** es un bot de Discord simple y potente diseñado para una sola tarea: permitirte gestionar tu servidor de Minecraft directamente desde Discord con comandos de barra (`/`).

Olvídate de conectarte por SSH para iniciar o detener tu servidor.


## Características Principales

-   **Control Total del Servidor**: Inicia y detiene tu servidor de Minecraft de forma segura utilizando sesiones `tmux`.
-   **Monitoreo en Tiempo Real**: Comprueba si tu servidor está `Online` u `Offline` en cualquier momento con un simple comando.
-   **Gestión de Permisos**: Asegura que solo los roles que tú elijas (ej. 'Admin') puedan ejecutar comandos sensibles como `/server_stop`.
-   **Fácil de Usar**: Integración nativa con los comandos de barra (`/`) de Discord para una experiencia de usuario moderna y limpia.
-   **Ligero y Enfocado**: Sin dependencias innecesarias. Solo hace una cosa y la hace bien 🔥😎

## Requisitos Previos

-   **Python 3.10.0 o superior**.
-   Un servidor de Minecraft configurado para ejecutarse con un script (ej. `start.sh`).
-   **`tmux`** instalado en la máquina que aloja tanto el bot como el servidor de Minecraft. Puedes instalarlo con `sudo apt install tmux` (Debian/Ubuntu) o `sudo yum install tmux` (CentOS).

## Instalación

Instala el bot directamente desde GitHub con `pip`:

```bash
pip install git+https://github.com/CalumRakk/minecontrol.git
```

## Configuración

El bot se configura mediante un único archivo de entorno (`.env`). Crea un archivo llamado `config.env` (o como prefieras) y rellena las siguientes variables:

```ini
# --- Configuración de Discord ---
# El token de tu aplicación de bot de Discord.
DISCORD_BOT_TOKEN="AQUÍ_TU_TOKEN_DE_DISCORD"

# (Opcional) El ID de tu servidor de Discord.
# Ayuda a que los comandos se registren más rápido durante el desarrollo.
DISCORD_GUILD_ID=123456789012345678

# --- Configuración del Servidor de Minecraft ---
# La ruta absoluta al directorio donde se encuentra tu servidor de Minecraft.
# Ejemplo: /home/user/minecraft_server
MINECRAFT_SERVER_PATH="/ruta/absoluta/a/tu/servidor/minecraft"

# La contraseña que configuraste en el archivo server.properties de tu servidor.
MINECRAFT_RCON_PASSWORD="TU_CONTRASEÑA_RCON"

# (Opcional) El host y puerto para la conexión RCON.
# Por lo general, no necesitas cambiar estos valores.
MINECRAFT_RCON_HOST="127.0.0.1"
MINECRAFT_RCON_PORT=25575

# (Opcional) El nombre de la sesión de tmux que se creará.
MINECRAFT_TERMINAL_SESSION_NAME="minecraft"
```

## Uso

Para iniciar el bot, ejecuta el siguiente comando en tu terminal, apuntando a tu archivo de configuración:

```bash
minecontrol /ruta/completa/hacia/tu/config.env
```

El bot se conectará a Discord y estará listo para recibir comandos.

### Comandos Disponibles

-   `/setup <rolename>`: **(Requiere Permisos de Admin en Discord)**. Configura el rol que podrá usar los comandos de gestión del servidor. Ejemplo: `/setup Admin`.
-   `/server_start`: Inicia el servidor de Minecraft si está apagado.
-   `/server_stop`: Detiene el servidor de Minecraft si está encendido.
-   `/server_status`: Muestra si el servidor de Minecraft está `Online` u `Offline`.
-   `/echo <text>`: Un comando simple para verificar que el bot está respondiendo.