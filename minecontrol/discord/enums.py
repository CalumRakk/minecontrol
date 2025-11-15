from enum import Enum


class ServerStatus(Enum):
    ONLINE = "Online"
    OFFLINE = "Offline"
    STARTING = "Starting"
    UNKNOWN = "Unknown"
