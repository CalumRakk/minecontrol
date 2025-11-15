# script.py

import argparse
import asyncio
from pathlib import Path
from typing import Union

from minecontrol.config import load_config_orchestator
from minecontrol.discord.client import init_discord_client
from minecontrol.discord.handlers import register_handlers_discord


async def main(path: Union[Path, str]):
    path = Path(path) if isinstance(path, str) else path
    config = load_config_orchestator(path)

    print("Configurando bot de Discord...")
    discord_bot = init_discord_client(config.discord_config)
    register_handlers_discord(discord_bot, config)
    print("Bot de Discord configurado.")

    print("Iniciando bot de Discord...")
    await discord_bot.start(config.discord_config.bot_token)
    print("Bot de Discord iniciado.")


def run():
    """Función de entrada para el comando de consola."""
    parser = argparse.ArgumentParser(description="Inicia el bot de Discord.")
    parser.add_argument(
        "env_file", type=str, help="Ruta al archivo de configuración .env"
    )
    args = parser.parse_args()

    try:
        asyncio.run(main(args.env_file))
    except KeyboardInterrupt:
        print("\nCerrando bots...")
    except FileNotFoundError:
        print(
            f"Error: No se pudo encontrar el archivo de configuración en '{args.env_file}'"
        )


if __name__ == "__main__":
    run()
