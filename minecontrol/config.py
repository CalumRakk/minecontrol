from pathlib import Path
from typing import Union

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings


class DiscordConfig(BaseSettings):
    """Configuración específica para Discord."""

    bot_token: str = Field(..., description="Token del bot de Discord")
    guild_id: int = Field(
        ..., description="ID del servidor de Discord para pruebas (opcional)"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        env_prefix = "DISCORD_"


class MinecraftConfig(BaseSettings):
    """Configuración para la conexión RCON con el servidor de Minecraft."""

    rcon_host: str = Field(
        "127.0.0.1", description="IP o dominio del servidor de Minecraft"
    )
    rcon_port: int = Field(25575, description="Puerto RCON del servidor de Minecraft")
    rcon_password: str = Field(
        ..., description="Contraseña RCON del servidor de Minecraft"
    )

    # variables para la gestión del proceso
    server_path: str = Field(
        ..., description="Ruta absoluta al directorio del servidor de Minecraft"
    )
    terminal_session_name: str = Field(
        "minecraft", description="Nombre de la sesión de tmux para el servidor"
    )

    # variables para el apagado automático
    auto_shutdown_enabled: bool = Field(
        False, description="Habilita el apagado automático si el servidor está vacío."
    )
    auto_shutdown_idle_minutes: int = Field(
        15,
        description="Minutos que el servidor debe estar vacío antes de iniciar el apagado.",
    )
    auto_shutdown_countdown_seconds: int = Field(
        60,
        description="Segundos de cuenta atrás final antes de apagar, una vez que se ha anunciado.",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        env_prefix = "MINECRAFT_"


class ManagerConfig:
    def __init__(
        self,
        discord_config: DiscordConfig,
        minecraft_config: MinecraftConfig,
    ) -> None:
        self.discord_config = discord_config
        self.minecraft_config = minecraft_config


def load_config_orchestator(env_path: Union[Path, str] = ".env") -> ManagerConfig:
    """Carga la configuración combinada para el orquestador desde un archivo .env."""
    env_file = Path(env_path) if isinstance(env_path, str) else env_path
    if not env_file.exists():
        raise FileNotFoundError(f"El archivo de configuración {env_file} no existe.")

    try:
        discord_config = DiscordConfig(_env_file=env_file)  # type: ignore
        minecraft_config = MinecraftConfig(_env_file=env_file)  # type: ignore
        return ManagerConfig(
            discord_config=discord_config,
            minecraft_config=minecraft_config,
        )
    except ValidationError as e:
        print(f"Error en la configuración del archivo {env_file}:\n{e}")
        raise
