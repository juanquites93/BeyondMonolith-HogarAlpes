from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from marketplace_asignacion.infrastructure.database import Base


class TrabajoORM(Base):
    __tablename__ = "trabajos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(String(36), nullable=False)
    direccion: Mapped[str] = mapped_column(String(255), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(100), nullable=False)
    pais: Mapped[str] = mapped_column(String(100), nullable=False)
    codigo_postal: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    descripcion: Mapped[str] = mapped_column(String(500), nullable=False)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False)
    notas: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    estado: Mapped[str] = mapped_column(String(50), nullable=False, default="BORRADOR")
    proveedor_seleccionado_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True
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
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
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
