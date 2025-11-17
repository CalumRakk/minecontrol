# script.py

import argparse
import asyncio
import os
from pathlib import Path
from typing import Union

from minecontrol.config import load_config_orchestator
from minecontrol.discord_bot.client import init_discord_client
from minecontrol.discord_bot.handlers import register_handlers_discord


async def main(path: Union[Path, str]):
    path = Path(path) if isinstance(path, str) else path
    config = load_config_orchestator(path)

    print("Verificando requisitos del servidor de Minecraft...")
    server_path = Path(config.minecraft_config.server_path)
    start_script = server_path / "start.sh"

    if not start_script.exists():
        error_msg = f"Error Crítico: El script 'start.sh' no se encuentra en la ruta especificada: '{server_path}'"
        print(error_msg)
        raise FileNotFoundError(error_msg)

    if not os.access(start_script, os.X_OK):
        error_msg = f"Error Crítico: El script '{start_script}' no tiene permisos de ejecución. Ejecuta 'chmod +x {start_script}' en tu terminal."
        print(error_msg)
        raise PermissionError(error_msg)

    print("Requisitos verificados correctamente.")

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
    except (FileNotFoundError, PermissionError) as e:
        print(f"\nFallo en la comprobación inicial. El bot no se ha iniciado.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")


if __name__ == "__main__":
    run()
