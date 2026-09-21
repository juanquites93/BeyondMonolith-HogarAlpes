"""Comandos de aplicación (CQS)."""

from __future__ import annotations
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class IniciarVerificacionProveedor:
    proveedor_id: uuid.UUID
    trabajo_id: Optional[str] = None
    correlation_id: Optional[str] = None
    idempotency_key: Optional[str] = None


@dataclass
class AprobarVerificacionProveedor:
    proveedor_id: uuid.UUID
    correlation_id: Optional[str] = None
    idempotency_key: Optional[str] = None


@dataclass
class RechazarVerificacionProveedor:
    proveedor_id: uuid.UUID
    motivo: Optional[str] = None
    correlation_id: Optional[str] = None
    idempotency_key: Optional[str] = None


@dataclass
class AcreditarProveedor:
    proveedor_id: uuid.UUID
    correlation_id: Optional[str] = None
    idempotency_key: Optional[str] = None


@dataclass
class RevocarAcreditacionProveedor:
    proveedor_id: uuid.UUID
    acreditacion_id: Optional[uuid.UUID] = None
    correlation_id: Optional[str] = None
    idempotency_key: Optional[str] = None
