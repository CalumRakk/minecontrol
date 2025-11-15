import subprocess
from pathlib import Path
from typing import Sequence, cast

import discord

from minecontrol.config import MinecraftConfig
from minecontrol.discord_bot.enums import ServerStatus

from ..rcon_client import RCONAuthError, RCONConnectionError, SimpleRCONClient
from .guild_config import GuildConfigManager

# --- Utilidades ---


def exists_tmux_session(session_name: str) -> bool:
    """Comprueba si una sesión de tmux con el nombre dado existe. Devuelve True si existe, False si no."""
    check_process = subprocess.run(["tmux", "has-session", "-t", session_name])
    return check_process.returncode == 0


async def get_minecraft_server_status(config: MinecraftConfig) -> ServerStatus:
    """
    Verifica el estado real del servidor.
    """
    try:
        async with SimpleRCONClient(
            config.rcon_host, config.rcon_port, config.rcon_password
        ) as client:
            await client.execute("list")
        return ServerStatus.ONLINE
    except (RCONConnectionError, RCONAuthError) as e:
        return ServerStatus.OFFLINE
    except Exception as e:
        return ServerStatus.UNKNOWN


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
    interaction: discord.Interaction, config: MinecraftConfig
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
        subprocess.Popen(
            ["tmux", "new-session", "-s", session_name, "-d", str(start_script)]
        )
        await interaction.followup.send(
            f"¡Iniciando el servidor de Minecraft en la sesión de tmux `{session_name}`! Dale uno o dos minutos para que arranque."
        )

    except Exception as e:
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

    if exists_tmux_session(session_name) is False:
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
            f"El rol '{rolename}' ya existe y ha sido configurado como el rol de administrador. ¡Todo listo!", ephemeral=True
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
            f"Rol '{new_role.name}' creado con éxito. "
            "Ahora puedes usar los comandos restringidos a este rol.",
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
    else:
        await interaction.followup.send("**El servidor de Minecraft está Offline.**")
