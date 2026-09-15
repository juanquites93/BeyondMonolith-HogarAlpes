from __future__ import annotations
import uuid
from typing import List

from sqlalchemy.orm import Session

from notificaciones.application.outbox_port import OutboxStore
from notificaciones.domain.events import DomainEvent
from notificaciones.infrastructure.orm import OutboxORM


class SqlAlchemyOutboxStore(OutboxStore):
    def __init__(self, session: Session | None = None):
        # session puede ser inyectada o asignada externamente antes de store()
        self._session = session

    def bind(self, session: Session) -> None:
        self._session = session

    def store(self, eventos: List[DomainEvent]) -> None:
        if self._session is None:
            raise RuntimeError(
                "OutboxStore requiere una sesión de base de datos activa"
            )
        for evento in eventos:
            payload = self._serialize(evento)
            orm = OutboxORM(
                id=str(uuid.uuid4()),
                aggregate_type="Notificacion",
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
        # Serialización manual controlada para evitar problemas con UUID/datetime
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
        if hasattr(evento, "notificacion_id"):
            base["notificacion_id"] = (
                str(evento.notificacion_id) if evento.notificacion_id else None
            )
        if hasattr(evento, "destinatario_id"):
            base["destinatario_id"] = evento.destinatario_id
        if hasattr(evento, "tipo"):
            base["tipo"] = evento.tipo
        if hasattr(evento, "canal"):
            base["canal"] = evento.canal
        if hasattr(evento, "enviada_en"):
            base["enviada_en"] = (
                evento.enviada_en.isoformat() if evento.enviada_en else None
            )
        if hasattr(evento, "motivo"):
            base["motivo"] = evento.motivo
        return base
