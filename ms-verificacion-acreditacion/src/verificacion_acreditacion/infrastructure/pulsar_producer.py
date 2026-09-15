"""Productor Pulsar para publicar eventos de outbox."""

from __future__ import annotations
import json
import logging
from datetime import datetime
from typing import List

import pulsar

from verificacion_acreditacion.infrastructure.config import settings
from verificacion_acreditacion.infrastructure.pulsar_client import get_pulsar_client
from verificacion_acreditacion.infrastructure.orm import OutboxORM

logger = logging.getLogger(__name__)


class PulsarEventProducer:
    """Lee outbox y publica a Pulsar con contrato JSON completo."""

    def __init__(self, session_factory):
        self._session_factory = session_factory
        self._producer: pulsar.Producer | None = None

    def _get_producer(self) -> pulsar.Producer:
        if self._producer is None:
            client = get_pulsar_client()
            self._producer = client.create_producer(
                topic=settings.PULSAR_PRODUCER_TOPIC,
                producer_name=f"{settings.APP_NAME}-producer",
            )
        return self._producer

    def publish_pending(self, limit: int = 100) -> int:
        from sqlalchemy.orm import Session

        session: Session = self._session_factory()
        try:
            rows: List[OutboxORM] = (
                session.query(OutboxORM)
                .filter(OutboxORM.processed_at.is_(None))
                .order_by(OutboxORM.occurred_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
                .all()
            )
            producer = self._get_producer()
            for row in rows:
                message = self._build_message(row)
                producer.send(
                    json.dumps(message).encode("utf-8"),
                    properties={
                        "messageType": row.event_type,
                        "version": str(row.version),
                        "correlationId": row.correlation_id or "",
                    },
                )
                row.processed_at = datetime.utcnow()
                logger.info(
                    "Evento publicado a Pulsar",
                    extra={
                        "event_type": row.event_type,
                        "aggregate_id": row.aggregate_id,
                        "correlation_id": row.correlation_id,
                    },
                )
            session.commit()
            return len(rows)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _build_message(row: OutboxORM) -> dict:
        return {
            "messageId": str(row.id),
            "messageType": row.event_type,
            "version": row.version,
            "occurredAt": row.occurred_at.isoformat() if row.occurred_at else None,
            "correlationId": row.correlation_id,
            "causationId": None,
            "idempotencyKey": row.id,
            "producer": settings.APP_NAME,
            "payload": row.payload,
        }
