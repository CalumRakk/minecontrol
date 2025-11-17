import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_LOCALE = "en"


class TranslationsManager:
    def __init__(self, locales_path: Path):
        self._translations: Dict[str, Dict[str, Any]] = {}
        self._load_translations(locales_path)

    def _load_translations(self, locales_path: Path):
        if not locales_path.is_dir():
            print(f"Advertencia: No se encontró el directorio local '{locales_path}'")
            return

        for file in locales_path.glob("*.json"):
            locale_name = file.stem
            try:
                with open(file, "r", encoding="utf-8") as f:
                    self._translations[locale_name] = json.load(f)
                print(f"Locale cargado: {locale_name}")
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error al cargar el locale '{locale_name}': {e}")

    def get_string(self, key: str, locale: str, **kwargs: Any) -> str:
        """
        Recupera una cadena traducida para una clave y un locale dados.
        Vuelve al locale predeterminado si no se encuentra la clave.

        Example: get_string("commands.start_server.already_running", "es", session_name="mc")
        """
        # Simplifica el locale (por ejemplo, 'en-US' -> 'en', 'es-ES' -> 'es')
        base_locale = str(locale).split("-")[0]

        # Obtener el diccionario para el locale solicitado, o usar el inglés por defecto
        locale_dict = self._translations.get(
            base_locale, self._translations.get(DEFAULT_LOCALE, {})
        )

        # Navegar por las claves anidadas (por ejemplo, "commands.start_server.already_running")
        keys = key.split(".")
        value = locale_dict
        try:
            for k in keys:
                value = value[k]
        except KeyError:
            # Si la clave no se encuentra en el locale solicitado, volver al predeterminado
            value_dict_fallback = self._translations.get(DEFAULT_LOCALE, {})
            try:
                for k in keys:
                    value_dict_fallback = value_dict_fallback[k]
                value = value_dict_fallback
            except KeyError:
                # Si la clave no se encuentra ni siquiera en el predeterminado, devolver un mensaje de error
                return f"!! Traducción faltante para la clave: {key} !!"

        if isinstance(value, str):
            try:
                return value.format(**kwargs)
            except KeyError as e:
                return f"!! Placeholder faltante {e} para la clave: {key} !!"

        # Esto puede suceder si la clave apunta a un diccionario, no a una cadena
        return f"!! Valor de traducción no válido para la clave: {key} !!"
