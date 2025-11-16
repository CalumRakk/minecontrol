import json
from pathlib import Path
from typing import Optional


class GuildConfigManager:
    """Gestiona la configuración específica de cada servidor (guild)."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config_data = self._load_config()

    def _load_config(self) -> dict:
        """Carga la configuración desde el archivo JSON."""
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_config(self):
        """Guarda la configuración actual en el archivo JSON."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, indent=4)

    def _get_or_create_guild_config(self, guild_id: int) -> dict:
        """Obtiene o crea la entrada de configuración para un guild."""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.config_data:
            self.config_data[guild_id_str] = {}
        return self.config_data[guild_id_str]

    def set_admin_role(self, guild_id: int, role_name: str):
        """Guarda el nombre del rol de administrador para un servidor."""
        guild_config = self._get_or_create_guild_config(guild_id)
        guild_config["admin_role"] = role_name
        self._save_config()

    def get_admin_role(self, guild_id: int) -> Optional[str]:
        """Obtiene el nombre del rol de administrador para un servidor."""
        guild_id_str = str(guild_id)
        return self.config_data.get(guild_id_str, {}).get("admin_role")

    def set_announcement_channel(self, guild_id: int, channel_id: int):
        """Guarda el ID del canal de anuncios para un servidor."""
        guild_config = self._get_or_create_guild_config(guild_id)
        guild_config["announcement_channel_id"] = channel_id
        self._save_config()

    def get_announcement_channel(self, guild_id: int) -> Optional[int]:
        """Obtiene el ID del canal de anuncios para un servidor."""
        guild_id_str = str(guild_id)
        return self.config_data.get(guild_id_str, {}).get("announcement_channel_id")
