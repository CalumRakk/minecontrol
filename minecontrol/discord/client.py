import logging
from typing import Optional

import discord
from discord.ext import commands

from minecontrol.config import DiscordConfig

logger = logging.getLogger(__name__)
_client_instance = None


def init_discord_client(settings: Optional[DiscordConfig] = None) -> commands.Bot:
    """Inicializa y devuelve el cliente del bot de Discord."""
    global _client_instance
    if _client_instance:
        return _client_instance

    logger.info("Iniciando cliente de Discord")

    intents = discord.Intents.default()

    bot = commands.Bot(command_prefix="!", intents=intents)

    logger.info("Cliente de Discord inicializado correctamente")
    _client_instance = bot
    return bot
