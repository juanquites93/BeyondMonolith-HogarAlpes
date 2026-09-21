from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field


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
class CotizacionSolicitada(DomainEvent):
    cotizacion_id: uuid.UUID = None
    trabajo_id: uuid.UUID = None
    proveedor_id: Optional[uuid.UUID] = None
    monto: Optional[float] = None
    moneda: str = "COP"
    descripcion: str = ""


@dataclass
class CotizacionCancelada(DomainEvent):
    cotizacion_id: uuid.UUID = None
    trabajo_id: uuid.UUID = None
    proveedor_id: Optional[uuid.UUID] = None
    cancelada_en: datetime = field(default_factory=datetime.utcnow)
