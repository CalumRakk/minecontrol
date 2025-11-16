from enum import Enum


class ServerStatus(Enum):
    ONLINE = "Online"
    OFFLINE = "Offline"
    STARTING = "Starting"
    UNKNOWN = "Unknown"


class AutoShutdownStatus(Enum):
    """
    Estados del ciclo de auto-apagado.

    Nombrados según la acción que el sistema está realizando.
    """

    # Hay jugadores. El sistema solo observa.
    MONITORING = "Monitoring"
    # No hay jugadores. Cronometrando el tiempo de inactividad.
    TIMING_EMPTY = "Timing Empty"
    # Cuenta atrás final para el apagado.
    SHUTDOWN_COUNTDOWN = "Shutdown Countdown"
