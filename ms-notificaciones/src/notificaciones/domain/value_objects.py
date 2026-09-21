from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class EstadoNotificacion(str, Enum):
    PENDIENTE = "PENDIENTE"
    ENVIADA = "ENVIADA"
    FALLIDA = "FALLIDA"
    CANCELADA = "CANCELADA"


class Canal(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"


@dataclass(frozen=True)
class Destinatario:
    id: str
    nombre: str
    contacto: Optional[str] = None
