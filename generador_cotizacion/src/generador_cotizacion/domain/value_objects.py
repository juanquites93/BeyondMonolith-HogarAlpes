from __future__ import annotations
from enum import Enum


class EstadoCotizacion(str, Enum):
    SOLICITADA = "SOLICITADA"
    ENVIADA = "ENVIADA"
    ACEPTADA = "ACEPTADA"
    RECHAZADA = "RECHAZADA"
    CANCELADA = "CANCELADA"
