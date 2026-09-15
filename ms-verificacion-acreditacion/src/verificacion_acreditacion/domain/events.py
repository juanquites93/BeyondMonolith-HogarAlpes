"""Eventos de dominio e integración."""

from __future__ import annotations
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List


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
class VerificacionProveedorIniciada(DomainEvent):
    verificacion_id: uuid.UUID = None
    proveedor_id: uuid.UUID = None
    iniciada_en: datetime = field(default_factory=datetime.utcnow)


@dataclass
class VerificacionProveedorAprobada(DomainEvent):
    verificacion_id: uuid.UUID = None
    proveedor_id: uuid.UUID = None
    aprobada_en: datetime = field(default_factory=datetime.utcnow)


@dataclass
class VerificacionProveedorRechazada(DomainEvent):
    verificacion_id: uuid.UUID = None
    proveedor_id: uuid.UUID = None
    motivo: Optional[str] = None
    rechazada_en: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ProveedorAcreditado(DomainEvent):
    proveedor_id: uuid.UUID = None
    acreditacion_id: uuid.UUID = None
    acreditado_en: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ProveedorNoAcreditado(DomainEvent):
    proveedor_id: uuid.UUID = None
    acreditacion_id: uuid.UUID = None
    motivo: Optional[str] = None
    no_acreditado_en: datetime = field(default_factory=datetime.utcnow)
