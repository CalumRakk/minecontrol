import json
import time
from pathlib import Path

STATE_FILE_PATH = Path(".server_state.json")
STARTING_TIMEOUT_SECONDS = 120  # 2 minutos


class ServerStateManager:
    """Gestiona un estado simple y persistente para el servidor de Minecraft."""

    def set_starting(self) -> None:
        """Marca el servidor como 'iniciando' guardando la marca de tiempo actual."""
        state = {"status": "starting", "timestamp": time.time()}
        STATE_FILE_PATH.write_text(json.dumps(state), encoding="utf-8")

    def set_stopped(self) -> None:
        """Elimina el archivo de estado para marcar el servidor como detenido."""
        if STATE_FILE_PATH.exists():
            STATE_FILE_PATH.unlink()

    def is_starting(self) -> bool:
        """
        Comprueba si el servidor está en el período de gracia de 'iniciando'.
        Devuelve True si el archivo de estado existe y no ha expirado.
        """
        if not STATE_FILE_PATH.exists():
            return False

        try:
            state = json.loads(STATE_FILE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return False

        if "timestamp" not in state:
            return False

        elapsed_time = time.time() - state["timestamp"]
        if elapsed_time < STARTING_TIMEOUT_SECONDS:
            return True

        self.set_stopped()
        return False
