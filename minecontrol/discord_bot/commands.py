import asyncio
import subprocess
from pathlib import Path
from typing import Sequence, cast

import discord
from discord.ext import commands

from minecontrol.config import MinecraftConfig
from minecontrol.discord_bot.enums import ServerStatus
from minecontrol.discord_bot.server_state import ServerStateManager

from ..rcon_client import RCONAuthError, RCONConnectionError, SimpleRCONClient
from .guild_config import GuildConfigManager

state_manager = ServerStateManager()

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

        # Si RCON funciona, el servidor está online
        state_manager.set_stopped()
        return ServerStatus.ONLINE

    except (RCONConnectionError, RCONAuthError):
        if state_manager.is_starting():
            return ServerStatus.STARTING
        return ServerStatus.OFFLINE

    except Exception:
        if state_manager.is_starting():
            return ServerStatus.STARTING
        return ServerStatus.UNKNOWN


# --- Tareas en segundo plano ---


async def check_and_announce_startup(
    bot: commands.Bot,
    config: MinecraftConfig,
    guild_id: int,
    config_manager: GuildConfigManager,
):
    """
    Espera 60s, comprueba si el servidor está online y lo anuncia si es así.
    """
    await asyncio.sleep(60)  # Espera un minuto

    status = await get_minecraft_server_status(config)
    if status != ServerStatus.ONLINE:
        return

    channel_id = config_manager.get_announcement_channel(guild_id)
    if not channel_id:
        print(
            f"Servidor online, pero no hay canal de anuncios configurado para el guild {guild_id}"
        )
        return

    channel = bot.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        print(f"Error: No se encontró el canal de anuncios con ID {channel_id}")
        return

    try:
        embed = discord.Embed(
            title="Servidor de Minecraft Online",
            description="El servidor de Minecraft ya está disponible para jugar.",
            color=discord.Color.green(),
        )
        embed.set_footer(text="¡Nos vemos dentro!")
        await channel.send(embed=embed)
    except discord.Forbidden:
        print(
            f"Error: No tengo permisos para enviar mensajes en el canal '{channel.name}'."
        )
    except Exception as e:
        print(f"Error inesperado al enviar el anuncio: {e}")


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
    interaction: discord.Interaction, config: MinecraftConfig
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
        state_manager.set_stopped()
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

    guild_permissions = cast(
        discord.Permissions, getattr(interaction.user, "guild_permissions", None)
    )
    if guild_permissions is None or not guild_permissions.administrator:
        await interaction.followup.send(
            "Debes ser administrador del servidor para usar este comando."
        )
        return

    config_manager.set_announcement_channel(interaction.guild.id, channel.id)  # type: ignore
    await interaction.followup.send(
        f"Perfecto. Los anuncios del servidor se enviarán ahora en el canal {channel.mention}."
    )
