from __future__ import annotations
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class SolicitarTrabajo:
    cliente_id: uuid.UUID
    direccion: str
    ciudad: str
    pais: str
    codigo_postal: Optional[str] = None
    descripcion: str = ""
    categoria: str = ""
    notas: Optional[str] = None
    correlation_id: Optional[str] = None


@dataclass
class PublicarTrabajo:
    trabajo_id: uuid.UUID
    correlation_id: Optional[str] = None


@dataclass
class SeleccionarProveedor:
    trabajo_id: uuid.UUID
    proveedor_id: uuid.UUID
    correlation_id: Optional[str] = None
