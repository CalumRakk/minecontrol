import discord
from discord.ext import commands

from .guild_config import GuildConfigManager


async def send_announcement(
    bot: commands.Bot,
    guild_manager: GuildConfigManager,
    guild_id: int,
    title: str,
    description: str,
    color: discord.Color,
    footer_text: str | None = None,
):
    """
    Función centralizada para enviar anuncios a un canal preconfigurado.
    """
    channel_id = guild_manager.get_announcement_channel(guild_id)
    if not channel_id:
        print(
            f"ANUNCIO: No hay canal de anuncios configurado para el guild {guild_id}. Se omite el mensaje: '{title}'"
        )
        return

    channel = bot.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        print(
            f"Error en Anuncio: No se encontró el canal de anuncios con ID {channel_id}"
        )
        return

    try:
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
        )
        if footer_text:
            embed.set_footer(text=footer_text)

        await channel.send(embed=embed)
        print(f"Anuncio enviado a '{channel.name}': '{title}'")

    except discord.Forbidden:
        print(
            f"Error en Anuncio: No tengo permisos para enviar mensajes en el canal '{channel.name}'."
        )
    except Exception as e:
        print(f"Error inesperado al enviar el anuncio: {e}")
