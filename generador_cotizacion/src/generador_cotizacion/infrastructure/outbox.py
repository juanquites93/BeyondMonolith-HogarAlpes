from __future__ import annotations
import uuid
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from generador_cotizacion.application.outbox_port import OutboxStore
from generador_cotizacion.domain.events import DomainEvent
from generador_cotizacion.infrastructure.orm import OutboxORM


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
                aggregate_type="Cotizacion",
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
        if hasattr(evento, "cotizacion_id"):
            base["cotizacion_id"] = (
                str(evento.cotizacion_id) if evento.cotizacion_id else None
            )
        if hasattr(evento, "trabajo_id"):
            base["trabajo_id"] = str(evento.trabajo_id) if evento.trabajo_id else None
        if hasattr(evento, "proveedor_id"):
            base["proveedor_id"] = (
                str(evento.proveedor_id) if evento.proveedor_id else None
            )
        if hasattr(evento, "monto"):
            base["monto"] = evento.monto
        if hasattr(evento, "moneda"):
            base["moneda"] = evento.moneda
        if hasattr(evento, "descripcion"):
            base["descripcion"] = evento.descripcion
        return base
