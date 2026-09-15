"""Eventos de integración generados desde la capa de aplicación."""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class IntegrationEvent:
    """Base para eventos de integración."""

    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    version: int = field(default=1)
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    aggregate_id: Optional[uuid.UUID] = None
    event_type: str = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "event_type", self.__class__.__name__)


# ── Verificación y Acreditación ──────────────────────────────


@dataclass
class ProveedorSeleccionadoParaValidacion(IntegrationEvent):
    """Evento de integración emitido hacia Verificación y Acreditación."""

    proveedor_id: uuid.UUID = None
    trabajo_id: uuid.UUID = None


# ── Generador de Cotizaciones ────────────────────────────────


@dataclass
class GenerarCotizacionCommand(IntegrationEvent):
    """Comando de integración hacia MS Generador de Cotizaciones.

    Se emite cuando un trabajo es publicado para que el sistema de
    cotizaciones prepare una estimación de costos.
    """

    trabajo_id: uuid.UUID = None
    cliente_id: uuid.UUID = None
    ubicacion: Optional[dict] = None
    alcance: Optional[dict] = None


# ── Notificaciones y Comunicaciones ──────────────────────────


@dataclass
class NotificarProveedorAsignadoCommand(IntegrationEvent):
    """Comando de integración hacia MS Notificaciones.

    Notifica al proveedor que fue asignado a un trabajo.
    """

    proveedor_id: uuid.UUID = None
    trabajo_id: uuid.UUID = None
    cliente_id: uuid.UUID = None
    detalles_trabajo: Optional[dict] = None


@dataclass
class NotificarClienteProveedorAsignadoCommand(IntegrationEvent):
    """Comando de integración hacia MS Notificaciones.

    Notifica al cliente que un proveedor fue asignado a su trabajo.
    """

    cliente_id: uuid.UUID = None
    trabajo_id: uuid.UUID = None
    proveedor_id: uuid.UUID = None


# ── Eventos compartidos / broadcast ──────────────────────────


@dataclass
class ProveedorAsignadoAlTrabajo(IntegrationEvent):
    """Evento de integración broadcast.

    Indica que un proveedor fue asignado a un trabajo.
    Puede ser consumido por cualquier MS interesado.
    """

    trabajo_id: uuid.UUID = None
    proveedor_id: uuid.UUID = None
    cliente_id: uuid.UUID = None
    asignado_en: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TrabajoActualizado(IntegrationEvent):
    """Evento de integración broadcast.

    Se emite cuando el trabajo cambia de estado relevante.
    """

    trabajo_id: uuid.UUID = None
    cliente_id: uuid.UUID = None
    estado_anterior: Optional[str] = None
    estado_nuevo: Optional[str] = None
    actualizado_en: datetime = field(default_factory=datetime.utcnow)
