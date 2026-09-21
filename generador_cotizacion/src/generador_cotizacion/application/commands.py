from __future__ import annotations
import uuid
from datetime import datetime
from dataclasses import dataclass
from typing import Optional


@dataclass
class SolicitarCotizacion:
    trabajo_id: uuid.UUID
    proveedor_id: uuid.UUID
    monto: float
    descripcion: str
    moneda: str = "COP"
    fecha_validez: Optional[datetime] = None
    correlation_id: Optional[str] = None


@dataclass
class GenerarCotizacion:
    """Comando disparado por el mensaje `GenerarCotizacionCommand` de Pulsar.

    A diferencia de `SolicitarCotizacion` (flujo HTTP con proveedor conocido),
    este comando llega sin proveedor ni monto: solo notifica que un trabajo fue
    publicado y necesita una cotización.
    """

    trabajo_id: uuid.UUID
    descripcion: str
    correlation_id: Optional[str] = None
    idempotency_key: Optional[str] = None


@dataclass
class ActualizarCotizacion:
    cotizacion_id: uuid.UUID
    proveedor_id: Optional[uuid.UUID] = None
    monto: Optional[float] = None
    descripcion: Optional[str] = None
    estado: Optional[str] = None
    fecha_validez: Optional[datetime] = None


@dataclass
class EliminarCotizacion:
    cotizacion_id: uuid.UUID


@dataclass
class CancelarCotizacion:
    cotizacion_id: uuid.UUID
    correlation_id: Optional[str] = None
    idempotency_key: Optional[str] = None
