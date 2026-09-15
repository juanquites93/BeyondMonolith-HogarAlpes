"""Schemas de la API REST."""

from __future__ import annotations
import uuid
from typing import Optional
from pydantic import BaseModel, Field


class IniciarVerificacionRequest(BaseModel):
    proveedor_id: uuid.UUID
    correlation_id: Optional[str] = Field(default=None)
    idempotency_key: Optional[str] = Field(default=None)


class AprobarVerificacionRequest(BaseModel):
    correlation_id: Optional[str] = Field(default=None)
    idempotency_key: Optional[str] = Field(default=None)


class RechazarVerificacionRequest(BaseModel):
    motivo: Optional[str] = Field(default=None)
    correlation_id: Optional[str] = Field(default=None)
    idempotency_key: Optional[str] = Field(default=None)


class AcreditarProveedorRequest(BaseModel):
    proveedor_id: uuid.UUID
    correlation_id: Optional[str] = Field(default=None)
    idempotency_key: Optional[str] = Field(default=None)


class ProveedorResponse(BaseModel):
    proveedor_id: uuid.UUID
    estado_verificacion: str
    estado_acreditacion: str

    class Config:
        from_attributes = True
