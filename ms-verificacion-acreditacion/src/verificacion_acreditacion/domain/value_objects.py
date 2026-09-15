"""Objetos valor del dominio."""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class EstadoVerificacion(str, Enum):
    PENDIENTE = "PENDIENTE"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"


class EstadoAcreditacion(str, Enum):
    NO_ACREDITADO = "NO_ACREDITADO"
    EN_TRAMITE = "EN_TRAMITE"
    ACREDITADO = "ACREDITADO"
    RECHAZADA = "RECHAZADA"


@dataclass(frozen=True)
class Evidencia:
    tipo: str
    url: str
    descripcion: Optional[str] = None
