from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass, field


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


# Eventos de dominio base
@dataclass
class DomainEvent:
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    version: int = field(default=1)
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    aggregate_id: Optional[uuid.UUID] = None
    event_type: str = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "event_type", self.__class__.__name__)


@dataclass
class TrabajoSolicitado(DomainEvent):
    trabajo_id: uuid.UUID = None
    cliente_id: uuid.UUID = None
    ubicacion: Optional[Ubicacion] = None
    alcance: Optional[Alcance] = None


@dataclass
class TrabajoPublicado(DomainEvent):
    trabajo_id: uuid.UUID = None
    cliente_id: uuid.UUID = None
    publicado_en: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ProveedoresInvitados(DomainEvent):
    trabajo_id: uuid.UUID = None
    proveedores_ids: List[uuid.UUID] = field(default_factory=list)


@dataclass
class ProveedorSeleccionado(DomainEvent):
    trabajo_id: uuid.UUID = None
    proveedor_id: uuid.UUID = None
    seleccionado_en: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AlcanceCambiado(DomainEvent):
    trabajo_id: uuid.UUID = None
    nuevo_alcance: Optional[Alcance] = None
    razon: Optional[str] = None
