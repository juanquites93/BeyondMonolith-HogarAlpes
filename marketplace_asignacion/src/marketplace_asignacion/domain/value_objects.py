from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class EstadoTrabajo(str, Enum):
    BORRADOR = "BORRADOR"
    SOLICITADO = "SOLICITADO"
    PUBLICADO = "PUBLICADO"
    EN_ASIGNACION = "EN_ASIGNACION"
    PROVEEDOR_SELECCIONADO = "PROVEEDOR_SELECCIONADO"


@dataclass(frozen=True)
class Ubicacion:
    direccion: str
    ciudad: str
    pais: str
    codigo_postal: Optional[str] = None


@dataclass(frozen=True)
class Alcance:
    descripcion: str
    categoria: str
    notas: Optional[str] = None
