import asyncio
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Sequence, cast

import discord
from discord.ext import commands

from minecontrol.config import MinecraftConfig
from minecontrol.discord_bot.enums import ServerStatus
from minecontrol.discord_bot.server_state import ServerStateManager

from ..rcon_client import RCONAuthError, RCONConnectionError, SimpleRCONClient
from .guild_config import GuildConfigManager
from .utils import send_announcement

state_manager = ServerStateManager()
_backup_in_progress = False

# --- Utilidades ---

def exists_tmux_session(session_name: str) -> bool:
    """Comprueba si una sesión de tmux con el nombre dado existe. Devuelve True si existe, False si no."""
    check_process = subprocess.run(["tmux", "has-session", "-t", session_name])
    return check_process.returncode == 0


async def get_minecraft_server_status(config: MinecraftConfig) -> ServerStatus:
    """
    Verifica el estado real del servidor, considerando el estado 'iniciando'.
    """
    try:
        async with SimpleRCONClient(
            config.rcon_host, config.rcon_port, config.rcon_password
        ) as client:
            await client.execute("list")
        return ServerStatus.ONLINE

    except (RCONConnectionError, RCONAuthError, asyncio.TimeoutError):
        if state_manager.is_starting():
            return ServerStatus.STARTING
        return ServerStatus.OFFLINE

    except Exception:
        if state_manager.is_starting():
            return ServerStatus.STARTING
        return ServerStatus.UNKNOWN


def get_leval_name(server_path: Path) -> str:
    props_file= server_path / "server.properties"
    level_name= "world"
    if props_file.exists():
        try:
            with open(props_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().lower().startswith("level-name="):
                        level_name = line.strip().split("=", 1)[1]
                        break
        except Exception:
            print("No se pudo leer el archivo server.properties para obtener el level-name.")
    return level_name


def perform_backup_zip(source_dir:Path, backup_folder:Path, world_name:str) -> Path:
    """
    Función bloqueante (CPU bound) que comprime la carpeta.
    Se ejecutará en un thread aparte.
    """
    timestamp= datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename= f"{world_name}_backup_{timestamp}"
    archive_path= backup_folder / filename

    final_path= shutil.make_archive(base_name= str(archive_path), format='zip', root_dir= source_dir, base_dir= world_name)
    return Path(final_path)


# --- Tareas en segundo plano ---


async def check_and_announce_startup(
    bot: commands.Bot,
    config: MinecraftConfig,
    guild_id: int,
    config_manager: GuildConfigManager,
):
    """
    Comprueba si el servidor se inicia y lo anuncia usando el módulo central.
    """
    max_wait_seconds = 240
    check_interval_seconds = 15
    attempts = max_wait_seconds // check_interval_seconds

    for i in range(attempts):
        status = await get_minecraft_server_status(config)
        if status == ServerStatus.ONLINE:
            await send_announcement(
                bot=bot,
                guild_manager=config_manager,
                guild_id=guild_id,
                title="Servidor de Minecraft Online",
                description="El servidor de Minecraft ya está disponible para jugar.",
                color=discord.Color.green(),
                footer_text="¡Nos vemos dentro!",
            )
            return

        print(
            f"Intento {i+1}/{attempts}: El servidor aún no está online. Reintentando en {check_interval_seconds}s..."
        )
        await asyncio.sleep(check_interval_seconds)

    print(
        f"El servidor no se inició después de {max_wait_seconds} segundos. Se cancela el anuncio."
    )


async def check_and_announce_shutdown(
    bot: commands.Bot,
    config: MinecraftConfig,
    guild_id: int,
    config_manager: GuildConfigManager,
):
    """
    Comprueba si el servidor se apaga y lo anuncia usando el módulo central.
    """
    max_wait_seconds = 120
    check_interval_seconds = 3
    attempts = max_wait_seconds // check_interval_seconds

    for i in range(attempts):
        status = await get_minecraft_server_status(config)
        if status == ServerStatus.OFFLINE:
            await send_announcement(
                bot=bot,
                guild_manager=config_manager,
                guild_id=guild_id,
                title="Servidor de Minecraft Desconectado",
                description="El servidor de Minecraft se ha desconectado.",
                color=discord.Color.red(),
                footer_text="¡Hasta pronto!",
            )
            return

        print(
            f"Intento {i+1}/{attempts}: El servidor aún no se desconectó. Reintentando en {check_interval_seconds}s..."
        )
        await asyncio.sleep(check_interval_seconds)

    print(
        f"El servidor no se desconectó en {max_wait_seconds} segundos. Se cancela el anuncio."
    )


# --- Comandos ---


async def echo(interaction: discord.Interaction, text: str):
    """
    Función de lógica para el comando echo.
    Responde a la interacción con el mismo texto proporcionado.
    """
    # El `ephemeral=True` aquí hace que el mensaje "pensando..." solo lo vea el usuario.
    await interaction.response.defer(ephemeral=True)

    # Enviamos la respuesta final usando followup.send()
    await interaction.followup.send(f"Dijiste: {text}")


async def start_minecraft_server(
    interaction: discord.Interaction,
    config: MinecraftConfig,
    config_manager: GuildConfigManager,
):
    """
    Inicia el servidor de Minecraft en una sesión 'tmux' si no está ya corriendo.
    """
    await interaction.response.defer(ephemeral=True)

    session_name = config.terminal_session_name
    if exists_tmux_session(session_name):
        await interaction.followup.send(
            f"El servidor de Minecraft ya está en ejecución en la sesión de tmux `{session_name}`."
        )
        return

    # 2. Si no existe, iniciarlo
    server_path = Path(config.server_path)
    start_script = server_path / "start.sh"

    if not start_script.exists():
        await interaction.followup.send(
            f"**Error:** No se encontró el script `start.sh` en la ruta `{server_path}`."
        )
        return

    current_status = await get_minecraft_server_status(config)
    if current_status == ServerStatus.ONLINE:
        await interaction.followup.send(
            "El servidor ya está online. No se necesita ninguna acción."
        )
        return

    try:

        guild_id = cast(int, interaction.guild_id)
        response_message = f"¡Iniciando el servidor en la sesión `{session_name}`!"
        if not config_manager.get_announcement_channel(guild_id):
            response_message += (
                "\n\n**Nota:** Para que anuncie públicamente cuando esté listo, "
                "configura un canal con `/set_announcement_channel`."
            )
        else:
            response_message += " Se anunciará públicamente cuando esté listo."

        state_manager.set_starting()
        subprocess.Popen(
            ["tmux", "new-session", "-s", session_name, "-d", str(start_script)]
        )

        await interaction.followup.send(response_message)

        bot = cast(commands.Bot, interaction.client)
        bot.loop.create_task(
            check_and_announce_startup(bot, config, guild_id, config_manager)
        )

    except Exception as e:
        state_manager.set_stopped()
        await interaction.followup.send(
            f"**Error inesperado al iniciar el servidor:**\n```\n{e}\n```"
        )


async def stop_minecraft_server(
    interaction: discord.Interaction,
    config: MinecraftConfig,
    config_manager: GuildConfigManager,
):
    """
    Envía el comando 'stop' a la sesión tmux del servidor de Minecraft.
    """
    await interaction.response.defer(ephemeral=True)
    session_name = config.terminal_session_name

    if not exists_tmux_session(session_name):
        state_manager.set_stopped()
        await interaction.followup.send(
            f"El servidor de Minecraft no está en ejecución. No se encontró la sesión de tmux `{session_name}`."
        )
        return

    current_status = await get_minecraft_server_status(config)
    if current_status == ServerStatus.OFFLINE:
        await interaction.followup.send(
            "El servidor ya está offline. No se necesita ninguna acción."
        )
        return

    try:
        guild_id = cast(int, interaction.guild_id)
        subprocess.run(
            [
                "tmux",
                "send-keys",
                "-t",
                session_name,
                "stop",
                "C-m",  # Enviamos el comando 'stop' y luego la tecla Enter (C-m)
            ]
        )

        bot = cast(commands.Bot, interaction.client)
        bot.loop.create_task(
            check_and_announce_shutdown(bot, config, guild_id, config_manager)
        )

        await interaction.followup.send(
            f"Comando de apagado enviado al servidor. La sesión de tmux `{session_name}` se cerrará en breve."
        )

    except Exception as e:
        await interaction.followup.send(
            f"**Error inesperado al intentar detener el servidor:**\n```\n{e}\n```"
        )


async def setup_bot_role(
    interaction: discord.Interaction, rolename: str, config_manager: GuildConfigManager
):
    """
    Verifica si el rol de admin existe y lo crea si es necesario.
    """
    await interaction.response.defer(ephemeral=True)

    # 1. Verificar si el USUARIO que ejecuta el comando es un admin del servidor
    guild_permissions = cast(
        discord.Permissions, getattr(interaction.user, "guild_permissions", None)
    )
    if guild_permissions is None or not guild_permissions.manage_roles:
        await interaction.followup.send(
            "Debes tener el permiso de 'Gestionar Roles' para ejecutar este comando.",
            ephemeral=True,
        )
        return

    # 2. Verificar si el BOT tiene permiso para gestionar roles
    bot_member = getattr(interaction.guild, "me", None)
    if bot_member is None or not bot_member.guild_permissions.manage_roles:
        await interaction.followup.send(
            "**¡Error crítico!** No tengo el permiso de 'Gestionar Roles'.\n"
            "Por favor, re-invítame con los permisos correctos o asígname un rol que los tenga.",
            ephemeral=True,
        )
        return

    # 3. Verificar si el rol ya existe
    roles: Sequence[discord.Role] = getattr(interaction.guild, "roles", [])
    existing_role = discord.utils.get(roles, name=rolename)
    if existing_role:
        config_manager.set_admin_role(interaction.guild.id, rolename)  # type: ignore
        await interaction.followup.send(
            f"El rol '{rolename}' ya existe y ha sido configurado como el rol de administrador. ¡Todo listo!",
            ephemeral=True,
        )
        return

    # 4. Si no existe, crearlo
    try:
        new_role = await interaction.guild.create_role(  # type: ignore
            name=rolename,
            reason=f"Rol requerido por {bot_member.display_name} para la administración.",
        )
        config_manager.set_admin_role(interaction.guild.id, rolename)  # type: ignore
        await interaction.followup.send(
            f"El rol '{rolename}' ha sido configurado como rol de administrador.\n\n"
            "**Siguiente paso recomendado:** Usa el comando `/set_announcement_channel` "
            "en el canal donde quieras que anuncie cuando el servidor esté online.",
            ephemeral=True,
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "No pude crear el rol. Asegúrate de que mi rol esté en una posición alta en la jerarquía de roles.",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.followup.send(
            f"Ocurrió un error inesperado al crear el rol: {e}", ephemeral=True
        )


async def check_server_status(
    interaction: discord.Interaction, config: MinecraftConfig
):
    """
    Muestra el estado actual y real del servidor de Minecraft.
    """
    await interaction.response.defer(ephemeral=True)
    status = await get_minecraft_server_status(config)

    if status == ServerStatus.ONLINE:
        await interaction.followup.send("**El servidor de Minecraft está Online.**")
    elif status == ServerStatus.STARTING:
        await interaction.followup.send(
            "**El servidor de Minecraft se está iniciando...** Por favor, espera un momento."
        )
    else:  # OFFLINE o UNKNOWN
        await interaction.followup.send("**El servidor de Minecraft está Offline.**")


async def set_announcement_channel_logic(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    config_manager: GuildConfigManager,
):
    """
    Configura el canal para los anuncios del servidor.
    """
    await interaction.response.defer(ephemeral=True)

    config_manager.set_announcement_channel(interaction.guild.id, channel.id)  # type: ignore
    await interaction.followup.send(
        f"Perfecto. Los anuncios del servidor se enviarán ahora en el canal {channel.mention}."
    )


async def backup_server(interaction: discord.Interaction, config: MinecraftConfig):
    global _backup_in_progress

    if _backup_in_progress:
        await interaction.response.send_message(
            "Ya hay un backup en progreso. Por favor, espera a que termine antes de iniciar otro.",
            ephemeral=True,
        )
        return

    _backup_in_progress = True

    try:
        await interaction.response.defer(ephemeral=False)

        server_path= Path(config.server_path)
        level_name= get_leval_name(server_path)
        world_path= server_path / level_name

        # Determinar dónde guardar el backup
        if Path(config.backup_path).is_absolute():
            backup_dir= Path(config.backup_path)
        else:
            backup_dir= server_path / config.backup_path

        backup_dir.mkdir(parents=True, exist_ok=True)

        if not world_path.exists():
            await interaction.followup.send(
                f"**Error:** No se encontró la carpeta del mundo `{level_name}` en la ruta `{world_path}`."
            )
            return
        
        status= await get_minecraft_server_status(config)
        is_online= status == ServerStatus.ONLINE

        try:
            if is_online:
                await interaction.followup.send(f"El servidor está online. Preparando para el backup...")

                async with SimpleRCONClient(
                    config.rcon_host, config.rcon_port, config.rcon_password
                ) as client:
                    # Poner el mundo en modo solo lectura
                    await client.execute("save-off")
                    await client.execute("save-all")

                    await asyncio.sleep(5)  # Esperar un momento para asegurar que se guarden los datos
            else:
                await interaction.followup.send(f"El servidor está offline. Iniciando el backup...")

            # Realiza la compresion

            await interaction.followup.send(f"Comprimiendo la carpeta del mundo `{level_name}`...")

            final_zip_path= await asyncio.to_thread(perform_backup_zip, source_dir= server_path, backup_folder= backup_dir, world_name= level_name)


            file_size_mb= final_zip_path.stat().st_size / (1024 * 1024)

            if is_online:
                async with SimpleRCONClient(
                    config.rcon_host, config.rcon_port, config.rcon_password
                ) as client:
                    # Volver a poner el mundo en modo escritura
                    await client.execute("save-on")
                    await client.execute(f"say Backup completado: {final_zip_path.name}.")
            
            await interaction.followup.send(
                f"Backup completado: `{final_zip_path.name}` ({file_size_mb:.2f} MB)."
            )
        except Exception as e:
            if is_online:
                try:
                    async with SimpleRCONClient(
                        config.rcon_host, config.rcon_port, config.rcon_password
                    ) as client:
                        await client.execute("save-on")
                except Exception:
                    # TODO: Si esto falla, tenemos grandes problemas.
                    # Significa que el mundo se queda en modo solo lectura.
                    pass
            await interaction.followup.send(
                f"**Error inesperado al crear el backup:**\n```\n{e}\n```"
            )        
    finally:
        _backup_in_progress = False