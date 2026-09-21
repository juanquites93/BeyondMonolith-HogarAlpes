"""Mapeo ORM para la Saga y su log de auditoría."""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ms_orquestador.infrastructure.database import Base


class SagaORM(Base):
    __tablename__ = "sagas"

    saga_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    trabajo_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    proveedor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    current_state: Mapped[str] = mapped_column(String(50), nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_event_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    payload_context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    compensated_steps: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class SagaLogORM(Base):
    __tablename__ = "saga_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    saga_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    message_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    causation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    message_type: Mapped[str] = mapped_column(String(100), nullable=False)
    producer: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )


class IdempotencyKeyORM(Base):
    __tablename__ = "idempotency_keys"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    command_type: Mapped[str] = mapped_column(String(100), nullable=False)
    response_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
