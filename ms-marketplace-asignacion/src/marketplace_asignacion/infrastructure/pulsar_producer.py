"""Productor Pulsar para publicar eventos de outbox a múltiples tópicos."""

from __future__ import annotations
import json
import logging
from datetime import datetime
from typing import List, Dict

import pulsar

from marketplace_asignacion.infrastructure.config import settings
from marketplace_asignacion.infrastructure.pulsar_client import get_pulsar_client
from marketplace_asignacion.infrastructure.orm import OutboxORM, DlqORM

logger = logging.getLogger(__name__)

# Mapeo estático: tipo de evento -> tópico Pulsar
_EVENT_TOPIC_MAP: Dict[str, str] = {
    # Dominio marketplace
    "TrabajoSolicitado": settings.PULSAR_PRODUCER_TOPIC,
    "TrabajoPublicado": settings.PULSAR_PRODUCER_TOPIC,
    "ProveedorSeleccionado": settings.PULSAR_PRODUCER_TOPIC,
    "AlcanceCambiado": settings.PULSAR_PRODUCER_TOPIC,
    # Verificación y Acreditación
    "ProveedorSeleccionadoParaValidacion": settings.PULSAR_VERIFICACION_TOPIC,
    # Cotizaciones
    "GenerarCotizacionCommand": settings.PULSAR_COTIZACIONES_TOPIC,
    # Notificaciones
    "NotificarProveedorAsignadoCommand": settings.PULSAR_NOTIFICACIONES_TOPIC,
    "NotificarClienteProveedorAsignadoCommand": settings.PULSAR_NOTIFICACIONES_TOPIC,
    # Broadcast compartidos
    "ProveedorAsignadoAlTrabajo": settings.PULSAR_PRODUCER_TOPIC,
    "TrabajoActualizado": settings.PULSAR_PRODUCER_TOPIC,
}

_DEFAULT_RETRIES = 3


class PulsarEventProducer:
    """Lee outbox y publica a Pulsar con contrato JSON completo.

    Soporta múltiples tópicos según el tipo de evento.
    Implementa reintentos básicos por evento.
    Si un mensaje agota reintentos, se mueve a la tabla DLQ local
    para evitar bloquear el outbox indefinidamente.
    """

    def __init__(self, session_factory, max_retries: int = _DEFAULT_RETRIES):
        self._session_factory = session_factory
        self._max_retries = max_retries
        self._producers: Dict[str, pulsar.Producer] = {}

    def _get_producer(self, topic: str) -> pulsar.Producer:
        if topic not in self._producers:
            client = get_pulsar_client()
            self._producers[topic] = client.create_producer(
                topic=topic,
                producer_name=f"{settings.APP_NAME}-producer",
            )
            logger.info("Pulsar producer creado", extra={"topic": topic})
        return self._producers[topic]

    def _resolve_topic(self, event_type: str) -> str:
        topic = _EVENT_TOPIC_MAP.get(event_type)
        if topic is None:
            logger.warning(
                "Tipo de evento sin tópico mapeado; usando tópico por defecto",
                extra={
                    "event_type": event_type,
                    "default_topic": settings.PULSAR_PRODUCER_TOPIC,
                },
            )
            topic = settings.PULSAR_PRODUCER_TOPIC
        return topic

    def publish_pending(self, limit: int = 100) -> dict:
        """Publica mensajes pendientes del outbox.

        Retorna un dict con contadores: {"published": int, "failed": int, "dlq": int}
        """
        from sqlalchemy.orm import Session

        session: Session = self._session_factory()
        published = 0
        failed = 0
        moved_to_dlq = 0

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
                try:
                    self._publish_one(row)
                    row.processed_at = datetime.utcnow()
                    session.commit()
                    published += 1
                except Exception as exc:
                    session.rollback()
                    # Mover a DLQ local para no bloquear el outbox
                    self._move_to_dlq(session, row, exc)
                    session.commit()
                    moved_to_dlq += 1
                    logger.warning(
                        "Mensaje movido a DLQ local",
                        extra={
                            "event_type": row.event_type,
                            "outbox_id": str(row.id),
                            "error": str(exc),
                        },
                    )

            return {"published": published, "failed": failed, "dlq": moved_to_dlq}
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _publish_one(self, row: OutboxORM) -> None:
        topic = self._resolve_topic(row.event_type)
        producer = self._get_producer(topic)
        message = self._build_message(row)
        payload_bytes = json.dumps(message).encode("utf-8")

        last_error = None
        for attempt in range(1, self._max_retries + 1):
            try:
                producer.send(
                    payload_bytes,
                    properties={
                        "messageType": row.event_type,
                        "version": str(row.version),
                        "correlationId": row.correlation_id or "",
                    },
                )
                logger.info(
                    "Evento publicado a Pulsar",
                    extra={
                        "event_type": row.event_type,
                        "topic": topic,
                        "aggregate_id": row.aggregate_id,
                        "correlation_id": row.correlation_id,
                        "attempt": attempt,
                    },
                )
                return
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Reintento de publicación",
                    extra={
                        "event_type": row.event_type,
                        "topic": topic,
                        "attempt": attempt,
                        "error": str(exc),
                    },
                )

        logger.error(
            "Publicación fallida tras máximo de reintentos",
            extra={
                "event_type": row.event_type,
                "topic": topic,
                "max_retries": self._max_retries,
                "error": str(last_error),
            },
        )
        raise last_error

    @staticmethod
    def _move_to_dlq(session, row: OutboxORM, error: Exception) -> None:
        dlq = DlqORM(
            id=str(row.id),  # reutilizamos el UUID del outbox como PK
            original_outbox_id=str(row.id),
            aggregate_type=row.aggregate_type,
            aggregate_id=row.aggregate_id,
            event_type=row.event_type,
            version=row.version,
            payload=row.payload,
            occurred_at=row.occurred_at,
            correlation_id=row.correlation_id,
            error_message=str(error)[:500],
            failed_at=datetime.utcnow(),
        )
        session.add(dlq)
        # Marcar outbox como procesado para que no se reintente más
        row.processed_at = datetime.utcnow()
        session.add(row)

    def retry_dlq(self, limit: int = 100) -> dict:
        """Reintenta publicar mensajes de la DLQ local.

        Retorna {"published": int, "failed": int, "dlq": int}
        """
        from sqlalchemy.orm import Session

        session: Session = self._session_factory()
        published = 0
        failed = 0
        moved_to_dlq = 0

        try:
            rows: List[DlqORM] = (
                session.query(DlqORM)
                .filter(DlqORM.reprocessed_at.is_(None))
                .order_by(DlqORM.failed_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
                .all()
            )

            for row in rows:
                try:
                    # Reconstruir un OutboxORM ficticio para reutilizar _publish_one
                    faux = OutboxORM(
                        id=row.original_outbox_id or row.id,
                        aggregate_type=row.aggregate_type,
                        aggregate_id=row.aggregate_id,
                        event_type=row.event_type,
                        version=row.version,
                        payload=row.payload,
                        occurred_at=row.occurred_at,
                        correlation_id=row.correlation_id,
                    )
                    self._publish_one(faux)
                    row.reprocessed_at = datetime.utcnow()
                    session.commit()
                    published += 1
                except Exception as exc:
                    session.rollback()
                    # Actualizar error y dejar en DLQ para próximo intento
                    row.error_message = f"Retry failed: {str(exc)[:400]}"
                    row.failed_at = datetime.utcnow()
                    session.add(row)
                    session.commit()
                    failed += 1

            return {"published": published, "failed": failed, "dlq": moved_to_dlq}
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
