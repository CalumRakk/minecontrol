🚧🔨👷‍♂️

    ⚠️ AVISO: Proyecto en Fase Inicial ⚠️
    
    MineControl se encuentra en sus primeras etapas de desarrollo. 
    Aunque es un proyecto seguro, es posible que hayan funcionalidades incompletas, 
    errores menores o comportamientos inesperados.


# MineControl

**MineControl** es un bot de Discord simple y potente diseñado para una sola tarea: permitirte gestionar el servidor de Minecraft que se ejecuta **en la misma máquina**, usando comandos de barra (`/`).

Olvídate de conectarte por SSH para un simple reinicio; MineControl actúa como tu operador local, dándote control directo desde Discord.


## Características Principales

-   **Gestión Directa del Proceso:** Inicia y detiene tu servidor de forma segura **en la misma máquina** utilizando sesiones `tmux`.
-   **Monitoreo en Tiempo Real:** Comprueba si tu servidor está `Online` u `Offline` en cualquier momento.
-   **Gestión de Permisos:** Asegura que solo los roles que tú elijas puedan ejecutar comandos sensibles.
-   **Fácil de Usar:** Integración nativa con los comandos de barra (`/`) de Discord.
-   **Ligero y Enfocado**: Solo hace una cosa y la hace bien 🔥😎

## Requisitos Previos

-   **Arquitectura Co-alojada:** El bot y tu servidor de Minecraft **deben** ejecutarse en la misma máquina.
-   **Python 3.10.0 o superior**.
-   **`tmux`** instalado en la máquina. Puedes instalarlo con `sudo apt install tmux` (Debian/Ubuntu) o `sudo yum install tmux` (CentOS).
-   Un **Script de Inicio** para tu servidor (ej. `start.sh`).

### Guía: Crear tu Script de Inicio (`start.sh`)

El bot no inicia el servidor de Minecraft directamente; en su lugar, ejecuta un script llamado `start.sh` que tú debes crear. Esto te da control total sobre cómo se inicia tu servidor (memoria, argumentos de Java, etc.).

Crea un archivo llamado `start.sh` en el directorio principal de tu servidor de Minecraft con el siguiente contenido, adaptándolo a tu tipo de servidor.

#### **Para Vanilla, Spigot o Paper**

Este es el script más común. Asegúrate de cambiar `server.jar` por el nombre de tu archivo `.jar` y ajusta la memoria (`-Xmx4G` significa 4 Gigabytes) a tus necesidades.

```bash
#!/bin/bash
# Navega al directorio donde se encuentra el script
cd "$(dirname "$0")"

# Ejecuta el servidor de Minecraft
java -Xmx4G -Xms1G -jar server.jar nogui
```

#### **Para Forge o Fabric**

Los servidores con mods a menudo usan un archivo `.jar` o un script de lanzamiento diferente. Revisa la documentación de tu versión de Forge/Fabric. El script podría verse así:

```bash
#!/bin/bash
# Navega al directorio donde se encuentra el script
cd "$(dirname "$0")"

# Ejemplo para Fabric (el nombre del .jar puede variar)
# java -Xmx4G -Xms1G -jar fabric-server-launch.jar nogui

# Ejemplo para Forge (a menudo usan scripts @user_jvm_args.txt y librerías)
# ./run.sh nogui
```

> [!IMPORTANT]
> **Hacer el script ejecutable**
>
> Después de crear o modificar tu `start.sh`, debes darle permisos de ejecución. Sin este paso, el bot no podrá iniciarlo. Ejecuta este comando en tu terminal:
>
> ```bash
> chmod +x start.sh
> ```


## Guía de Invitación del Bot

Antes de configurar los archivos, es crucial invitar al bot a tu servidor de Discord con los permisos correctos. Un enlace mal generado puede causar que los comandos no aparezcan o que ciertas funciones fallen.

Sigue estos pasos en el [Portal de Desarrolladores de Discord](https://discord.com/developers/applications) después de crear tu aplicación:

1.  Selecciona tu aplicación y ve a la pestaña **"OAuth2"** en el menú de la izquierda.
2.  Haz clic en la sub-pestaña **"URL Generator"**.
3.  En la sección **"SCOPES"**, marca las siguientes dos casillas:
    *   `bot`: Para identificar tu aplicación como un bot que puede unirse a servidores.
    *   `applications.commands`: Permite al bot crear y gestionar sus comandos de barra (`/`) en tu servidor. **¡Este es el permiso más importante para que los comandos sean visibles!**

4.  Una vez marcadas, aparecerá un nuevo cuadro de **"BOT PERMISSIONS"** más abajo. Aquí debes seleccionar los permisos que el bot necesita para operar. Para MineControl, activa los siguientes:
    *   **Gestionar Roles**: Esencial para que el comando `/setup <rolename>` pueda crear y asignar el rol de administrador del bot.
    *   **Enviar Mensajes**: Necesario para que el bot pueda responder a todos los comandos.
    *   **Insertar Enlaces**: Requerido para que los anuncios de estado del servidor (cuando está `Online`) se muestren correctamente, ya que usan un formato enriquecido (embeds).
    *   **Ver Canales**: Permite al bot ver los canales de tu servidor, un requisito básico para poder enviar mensajes en ellos.

5.  Con todo lo anterior seleccionado, se habrá generado una URL en la parte inferior de la página. Cópiala.
6.  Pega esa URL en tu navegador, elige el servidor al que quieres añadir el bot y autoriza los permisos.

¡Listo! Con esto, el bot tendrá todo lo necesario para funcionar sin problemas en tu servidor.

## Instalación

Instala el bot directamente desde GitHub con `pip`:

```bash
pip install git+https://github.com/CalumRakk/minecontrol.git
```

## Configuración

Configurar el bot es un proceso de dos pasos: primero, te aseguras de que tu servidor de Minecraft esté listo para recibir comandos remotos; segundo, le das al bot las credenciales para conectarse.

### 1. Habilitar RCON en tu Servidor

Para que MineControl pueda comunicarse con tu servidor, necesitas habilitar la consola remota (RCON).

1.  Abre el archivo `server.properties` que se encuentra en el directorio de tu servidor de Minecraft.
2.  Busca y modifica las siguientes líneas. Si no existen, añádelas:

    ```properties
    # server.properties
    enable-rcon=true
    rcon.password=UNA_CONTRASEÑA_MUY_SEGURA
    ```

> **Importante:** La `rcon.password` es la clave de acceso a la consola de tu servidor. Usa una contraseña larga, única y segura. No la compartas.

### 2. Crear el Archivo de Entorno del Bot

El bot se configura mediante un único archivo de entorno (`.env`). Crea un archivo llamado `config.env` (o como prefieras) y rellena las siguientes variables:

```ini
# --- Configuración de Discord ---
# El token de tu aplicación de bot de Discord. (Obligatorio)
DISCORD_BOT_TOKEN="AQUÍ_TU_TOKEN_DE_DISCORD"

# --- Configuración del Servidor de Minecraft ---
# La ruta absoluta al directorio de tu servidor. (Obligatorio)
MINECRAFT_SERVER_PATH="/ruta/absoluta/a/tu/servidor/minecraft"

# La contraseña RCON de tu archivo server.properties. (Obligatorio)
MINECRAFT_RCON_PASSWORD="TU_CONTRASEÑA_RCON"

# El ID de tu servidor de Discord. (Recomendado)
# Esto evita que pasen horas para que discord registre los comandos de tu bot de discord.
# Ve a Ajustes de Usuario > Avanzado y activa el 'Modo de desarrollador'. Luego, haz clic derecho en el icono de tu servidor y selecciona Copiar ID del servidor.
DISCORD_GUILD_ID=123456789012345678

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