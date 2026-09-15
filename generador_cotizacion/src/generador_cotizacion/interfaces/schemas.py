from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SolicitarCotizacionRequest(BaseModel):
    trabajo_id: uuid.UUID
    proveedor_id: uuid.UUID
    monto: float
    descripcion: str
    moneda: str = "COP"
    fecha_validez: Optional[datetime] = None
    correlation_id: Optional[str] = Field(
        default=None, description="Id de correlación para trazabilidad"
    )


class ActualizarCotizacionRequest(BaseModel):
    proveedor_id: Optional[uuid.UUID] = None
    monto: Optional[float] = None
    descripcion: Optional[str] = None
    estado: Optional[str] = None
    fecha_validez: Optional[datetime] = None


class CotizacionResponse(BaseModel):
    cotizacion_id: uuid.UUID
    trabajo_id: uuid.UUID
    proveedor_id: Optional[uuid.UUID] = None
    monto: Optional[float] = None
    moneda: str
    descripcion: str
    estado: str
    fecha_solicitud: datetime
    fecha_validez: Optional[datetime] = None

    class Config:
        from_attributes = True
