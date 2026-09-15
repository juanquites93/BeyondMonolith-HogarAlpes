"""Implementación de outbox con SQLAlchemy."""

from __future__ import annotations
import uuid
import dataclasses
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from verificacion_acreditacion.application.outbox_port import OutboxStore
from verificacion_acreditacion.domain.events import DomainEvent
from verificacion_acreditacion.infrastructure.orm import OutboxORM


class SqlAlchemyOutboxStore(OutboxStore):
    def __init__(self, session: Session | None = None):
        self._session = session

    def bind(self, session: Session) -> None:
        self._session = session

    def store(self, eventos: List[DomainEvent]) -> None:
        if self._session is None:
            raise RuntimeError("OutboxStore requiere una sesión activa")
        for evento in eventos:
            payload = self._serialize(evento)
            orm = OutboxORM(
                id=str(uuid.uuid4()),
                aggregate_type="Proveedor",
                aggregate_id=str(evento.aggregate_id) if evento.aggregate_id else None,
                event_type=evento.event_type,
                version=evento.version,
                payload=payload,
                occurred_at=evento.occurred_at,
                correlation_id=evento.correlation_id,
            )
            self._session.add(orm)

    @staticmethod
    def _serialize(evento: DomainEvent) -> dict:
        base = {
            "event_id": str(evento.event_id),
            "event_type": evento.event_type,
            "version": evento.version,
            "occurred_at": evento.occurred_at.isoformat()
            if evento.occurred_at
            else None,
            "correlation_id": evento.correlation_id,
            "aggregate_id": str(evento.aggregate_id) if evento.aggregate_id else None,
        }
        if hasattr(evento, "verificacion_id"):
            base["verificacion_id"] = (
                str(evento.verificacion_id) if evento.verificacion_id else None
            )
        if hasattr(evento, "proveedor_id"):
            base["proveedor_id"] = (
                str(evento.proveedor_id) if evento.proveedor_id else None
            )
        if hasattr(evento, "acreditacion_id"):
            base["acreditacion_id"] = (
                str(evento.acreditacion_id) if evento.acreditacion_id else None
            )
        if hasattr(evento, "motivo"):
            base["motivo"] = evento.motivo
        if hasattr(evento, "iniciada_en"):
            base["iniciada_en"] = (
                evento.iniciada_en.isoformat() if evento.iniciada_en else None
            )
        if hasattr(evento, "aprobada_en"):
            base["aprobada_en"] = (
                evento.aprobada_en.isoformat() if evento.aprobada_en else None
            )
        if hasattr(evento, "rechazada_en"):
            base["rechazada_en"] = (
                evento.rechazada_en.isoformat() if evento.rechazada_en else None
            )
        if hasattr(evento, "acreditado_en"):
            base["acreditado_en"] = (
                evento.acreditado_en.isoformat() if evento.acreditado_en else None
            )
        if hasattr(evento, "no_acreditado_en"):
            base["no_acreditado_en"] = (
                evento.no_acreditado_en.isoformat() if evento.no_acreditado_en else None
            )
        return base
