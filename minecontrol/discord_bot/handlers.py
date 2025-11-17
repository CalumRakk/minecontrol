from collections.abc import Sequence
from pathlib import Path
from typing import cast

import discord
from discord import app_commands
from discord.app_commands import AppCommandError, CheckFailure
from discord.ext import commands

from minecontrol.config import ManagerConfig
from minecontrol.discord_bot.guild_config import GuildConfigManager

from .commands import (
    check_server_status,
    echo,
    set_announcement_channel_logic,
    setup_bot_role,
    start_minecraft_server,
    stop_minecraft_server,
)
from .i18n import TranslationsManager
from .logging_utils import log_command_usage, setup_command_logger
from .tasks import auto_shutdown_loop

config_manager = GuildConfigManager(Path("guild_configs.json"))
command_logger = setup_command_logger()
log_command = log_command_usage(command_logger)
locales_path = Path(__file__).parent / "locales"
t = TranslationsManager(locales_path)


async def is_admin(interaction: discord.Interaction) -> bool:
    """
    Verifica si el usuario tiene el rol de admin configurado para este servidor.
    """
    locale = str(interaction.locale)

    # 1. Obtener el nombre del rol guardado para este servidor
    id_ = cast(int, getattr(interaction.guild, "id", None))
    admin_role_name = config_manager.get_admin_role(id_)
    if id_ is None or not admin_role_name:
        await interaction.response.send_message(
            t.get_string("commands.errors.admin_role_not_set", locale),
            ephemeral=True,
        )
        return False

    # 2. Verificar si el rol existe en el servidor
    roles: Sequence[discord.Role] = getattr(interaction.guild, "roles", [])
    role = discord.utils.get(roles, name=admin_role_name)
    if not role:
        await interaction.response.send_message(
            t.get_string(
                "commands.errors.user_not_admin", locale, role_name=admin_role_name
            ),
            ephemeral=True,
        )
        return False

    # 3. Verificar si el usuario tiene ese rol
    user_roles: Sequence[discord.Role] = getattr(interaction.user, "roles", [])
    if role not in user_roles:
        await interaction.response.send_message(
            f"No tienes el rol '{admin_role_name}' necesario para usar este comando.",
            ephemeral=True,
        )
        return False

    return True


def register_handlers_discord(bot: commands.Bot, config: ManagerConfig):
    """Registra los slash commands y eventos para el bot de Discord."""
    guild_obj = (
        discord.Object(id=config.discord_config.guild_id)
        if config.discord_config.guild_id
        else None
    )

    # --- Comandos Administrativos ---
    # Comando setup
    @bot.tree.command(
        name="setup",
        description="Configura el rol necesario para que los comandos de admin funcionen.",
        guild=guild_obj,
    )
    @app_commands.describe(
        rolename="El nombre del rol que se usará para los permisos (ej. 'Admin')"
    )
    @log_command
    async def setup(interaction: discord.Interaction, rolename: str):
        await setup_bot_role(interaction, rolename, config_manager)

    # Comando set_announcement_channel
    @bot.tree.command(
        name="set_announcement_channel",
        description="Configura el canal para anunciar cuando el servidor esté online.",
        guild=guild_obj,
    )
    @app_commands.describe(channel="El canal donde se enviarán los anuncios.")
    @app_commands.check(is_admin)
    @log_command
    async def set_announcement_channel(
        interaction: discord.Interaction, channel: discord.TextChannel
    ):
        await set_announcement_channel_logic(interaction, channel, config_manager)

    # Comando echo
    @bot.tree.command(
        name="echo",
        description="Repite el texto que envíes.",
        guild=guild_obj,
    )
    @app_commands.describe(text="El texto que quieres que repita.")
    @log_command
    async def echo_command(interaction: discord.Interaction, text: str):
        await echo(interaction, text)

    # Comando iniciar servidor
    @bot.tree.command(
        name="server_start",
        description="Inicia el servidor de Minecraft si está apagado.",
        guild=guild_obj,
    )
    @app_commands.check(is_admin)
    @log_command
    async def server_start(interaction: discord.Interaction):
        await start_minecraft_server(
            interaction,
            config.minecraft_config,
            config_manager,
            t,
            str(interaction.locale),
        )

    @server_start.error
    async def server_start_error(
        interaction: discord.Interaction, error: AppCommandError
    ):
        if isinstance(error, CheckFailure):
            print(
                f"Check 'is_admin' fallido para el usuario {interaction.user} en el comando /server_stop. Mensaje ya enviado."
            )
            return
        if isinstance(error, app_commands.MissingRole):
            await interaction.followup.send(
                "No tienes permiso para usar este comando.", ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"Ocurrió un error: {error}", ephemeral=True
            )

    # Comando detener servidor
    @bot.tree.command(
        name="server_stop",
        description="Detiene el servidor de Minecraft si estaba corriendo.",
        guild=guild_obj,
    )
    @app_commands.check(is_admin)
    @log_command
    async def server_stop(interaction: discord.Interaction):
        await stop_minecraft_server(
            interaction, config.minecraft_config, config_manager
        )

    @server_stop.error
    async def server_stop_error(
        interaction: discord.Interaction, error: AppCommandError
    ):
        if isinstance(error, CheckFailure):
            print(
                f"Check 'is_admin' fallido para el usuario {interaction.user} en el comando /server_stop. Mensaje ya enviado."
            )
            return

        if isinstance(error, app_commands.MissingRole):
            await interaction.followup.send(
                "No tienes permiso para usar este comando.", ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"Ocurrió un error: {error}", ephemeral=True
            )

    # Comando estado del servidor
    @bot.tree.command(
        name="server_status",
        description="Verifica si el servidor de Minecraft está online u offline.",
        guild=guild_obj,
    )
    @log_command
    async def server_status(interaction: discord.Interaction):
        await check_server_status(interaction, config.minecraft_config)

    # Evento que se ejecuta cuando el bot está listo
    @bot.event
    async def on_ready():
        print(f"Bot de Discord conectado como {bot.user}")
        try:
            guild = (
                discord.Object(id=config.discord_config.guild_id)
                if config.discord_config.guild_id
                else None
            )
            synced = await bot.tree.sync(guild=guild)
            print(f"Sincronizados {len(synced)} comandos.")
        except Exception as e:
            print(f"Error al sincronizar comandos: {e}")

        if (
            config.minecraft_config.auto_shutdown_enabled
            and config.discord_config.guild_id
        ):
            print("Iniciando tarea de auto-apagado del servidor.")
            auto_shutdown_loop.start(
                bot,
                config.minecraft_config,
                config_manager,
                config.discord_config.guild_id,
            )
        else:
            print(
                "La tarea de auto-apagado está deshabilitada o no se especificó un GUILD_ID."
            )
