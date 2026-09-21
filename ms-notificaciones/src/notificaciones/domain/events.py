from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field


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
class NotificacionSolicitada(DomainEvent):
    notificacion_id: uuid.UUID = None
    destinatario_id: str = None
    tipo: str = None
    canal: str = None


@dataclass
class NotificacionEnviada(DomainEvent):
    notificacion_id: uuid.UUID = None
    destinatario_id: str = None
    canal: str = None
    trabajo_id: Optional[str] = None
    enviada_en: datetime = field(default_factory=datetime.utcnow)


@dataclass
class NotificacionFallida(DomainEvent):
    notificacion_id: uuid.UUID = None
    destinatario_id: str = None
    canal: str = None
    trabajo_id: Optional[str] = None
    motivo: Optional[str] = None


@dataclass
class NotificacionCancelada(DomainEvent):
    notificacion_id: uuid.UUID = None
    destinatario_id: str = None
    canal: str = None
    trabajo_id: Optional[str] = None
    cancelada_en: datetime = field(default_factory=datetime.utcnow)
