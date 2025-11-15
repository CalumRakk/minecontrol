import functools
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from discord import Interaction


def setup_command_logger():
    """Configura y devuelve un logger para registrar el uso de comandos."""
    log_directory = "logs"
    Path(log_directory).mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("discord_commands")
    logger.setLevel(logging.INFO)

    log_format = logging.Formatter(
        "%(asctime)s - [%(levelname)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Evita handlers duplicados
    if logger.hasHandlers():
        logger.handlers.clear()

    # Handler para el archivo con rotacion diaria
    handler = TimedRotatingFileHandler(
        f"{log_directory}/command_usage.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    handler.setFormatter(log_format)
    logger.addHandler(handler)

    # Handler para la consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    return logger


def log_command_usage(logger: logging.Logger):
    """
    Un decorador que registra la información de una interacción de comando.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(interaction: Interaction, *args, **kwargs):
            # Extraer información de la interacción
            user = interaction.user
            command_name = (
                interaction.command.name if interaction.command else "unknown_command"
            )
            guild = interaction.guild.name if interaction.guild else "Direct Message"
            channel = (
                getattr(interaction.channel, "name")
                if hasattr(interaction.channel, "name")
                else f"ID({interaction.channel_id})"
            )

            # Formatear los argumentos del comando
            options = {k: v for k, v in interaction.namespace}

            log_message = (
                f"User: '{user}' (ID: {user.id}) | "
                f"Guild: '{guild}' | Channel: '#{channel}' | "
                f"Command: '/{command_name}' | "
                f"Options: {options}"
            )

            logger.info(log_message)

            # Ejecutar el comando original
            return await func(interaction, *args, **kwargs)

        return wrapper

    return decorator
