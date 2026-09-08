from __future__ import annotations
import logging
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from marketplace_asignacion.infrastructure.orm import OutboxORM

logger = logging.getLogger(__name__)


class SimulatedEventPublisher:
    """Publicador simulado que lee de la tabla outbox y emite eventos.

    En producción se reemplaza por:
    - Kafka Producer (exactly-once con idempotencia)
    - RabbitMQ Publisher confirm
    - AWS SNS/SQS
    """

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def publish_pending(self, limit: int = 100) -> int:
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
            for row in rows:
                self._publish_one(row)
                row.processed_at = datetime.utcnow()
            session.commit()
            return len(rows)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _publish_one(self, row: OutboxORM) -> None:
        # Simula envío al broker logueando estructuradamente
        logger.info(
            "[BROKER-SIMULADO] Publicando evento",
            extra={
                "event_type": row.event_type,
                "version": row.version,
                "aggregate_id": row.aggregate_id,
                "correlation_id": row.correlation_id,
                "payload": row.payload,
            },
        )
        # Retry básico simulado: si el tipo contiene "FALLA" podría fallar.
        # DLQ: en un broker real los mensajes que agotan reintentos van a DLQ.
        # Aquí documentamos el comportamiento esperado.
