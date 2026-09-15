"""Mapeo ORM."""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from verificacion_acreditacion.infrastructure.database import Base


class ProveedorORM(Base):
    __tablename__ = "proveedores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    estado_verificacion: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDIENTE"
    )
    estado_acreditacion: Mapped[str] = mapped_column(
        String(50), nullable=False, default="NO_ACREDITADO"
    )


class OutboxORM(Base):
    __tablename__ = "outbox"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class IdempotencyKeyORM(Base):
    __tablename__ = "idempotency_keys"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    command_type: Mapped[str] = mapped_column(String(100), nullable=False)
    response_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
