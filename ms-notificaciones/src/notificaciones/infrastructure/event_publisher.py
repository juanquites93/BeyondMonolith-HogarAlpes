from __future__ import annotations
import json
import logging
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from notificaciones.infrastructure.config import settings
from notificaciones.infrastructure.orm import OutboxORM

logger = logging.getLogger(__name__)


class SimulatedEventPublisher:
    """Lee la tabla outbox y publica los eventos pendientes.

    Si `PULSAR_SERVICE_URL` esta configurado, publica al cluster real (el
    equipo lo despliega, este servicio solo se conecta). Si no, simula la
    publicacion logueando estructuradamente, igual que hace el servicio de
    marketplace mientras no hay broker disponible.
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
        if settings.PULSAR_SERVICE_URL:
            self._publicar_en_pulsar(row)
        else:
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

    def _publicar_en_pulsar(self, row: OutboxORM) -> None:
        import pulsar

        mensaje = {
            "messageId": row.id,
            "messageType": row.event_type,
            "version": row.version,
            "occurredAt": row.occurred_at.isoformat(),
            "correlationId": row.correlation_id,
            "producer": settings.APP_NAME,
            "payload": row.payload,
        }
        client = pulsar.Client(settings.PULSAR_SERVICE_URL)
        try:
            topico = (
                f"persistent://{settings.PULSAR_TENANT}/{settings.PULSAR_NAMESPACE}/"
                "ms-notificaciones.eventos"
            )
            productor = client.create_producer(topico)
            productor.send(json.dumps(mensaje).encode("utf-8"))
        finally:
            client.close()
