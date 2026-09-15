from __future__ import annotations
import uuid
from typing import Optional

from pydantic import BaseModel, Field


class UbicacionSchema(BaseModel):
    direccion: str
    ciudad: str
    pais: str
    codigo_postal: Optional[str] = None


class AlcanceSchema(BaseModel):
    descripcion: str
    categoria: str
    notas: Optional[str] = None


class SolicitarTrabajoRequest(BaseModel):
    cliente_id: uuid.UUID
    ubicacion: UbicacionSchema
    alcance: AlcanceSchema
    correlation_id: Optional[str] = Field(
        default=None, description="Id de correlación para trazabilidad"
    )
    idempotency_key: Optional[str] = Field(
        default=None, description="Clave de idempotencia explícita"
    )


class PublicarTrabajoRequest(BaseModel):
    correlation_id: Optional[str] = None
    idempotency_key: Optional[str] = None


class SeleccionarProveedorRequest(BaseModel):
    proveedor_id: uuid.UUID
    correlation_id: Optional[str] = None
    idempotency_key: Optional[str] = None


class TrabajoResponse(BaseModel):
    trabajo_id: uuid.UUID
    cliente_id: uuid.UUID
    estado: str
    proveedor_seleccionado_id: Optional[uuid.UUID] = None
    ubicacion: Optional[UbicacionSchema] = None
    alcance: Optional[AlcanceSchema] = None

    class Config:
        from_attributes = True
