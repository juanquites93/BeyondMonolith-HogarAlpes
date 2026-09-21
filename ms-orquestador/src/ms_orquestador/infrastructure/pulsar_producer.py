"""Productor Pulsar del orquestador.

Publica comandos a los tópicos de destino usando el contrato de sobre común.
"""

from __future__ import annotations
import json
import logging
import uuid
from datetime import datetime
from typing import Dict

import pulsar

from ms_orquestador.infrastructure.config import settings
from ms_orquestador.infrastructure.pulsar_client import get_pulsar_client

logger = logging.getLogger(__name__)


class PulsarCommandProducer:
    """Publica comandos del orquestador hacia los microservicios participantes."""

    def __init__(self):
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

    def send_command(
        self,
        topic: str,
        message_type: str,
        payload: dict,
        saga_id: str,
        correlation_id: str,
        causation_id: str,
        idempotency_key: str,
    ) -> str:
        message_id = str(uuid.uuid4())
        message = {
            "messageId": message_id,
            "messageType": message_type,
            "version": "1.0",
            "occurredAt": datetime.utcnow().isoformat(),
            "sagaId": saga_id,
            "correlationId": correlation_id,
            "causationId": causation_id,
            "idempotencyKey": idempotency_key,
            "producer": settings.APP_NAME,
            "payload": payload,
        }

        producer = self._get_producer(topic)
        producer.send(
            json.dumps(message).encode("utf-8"),
            properties={
                "messageType": message_type,
                "version": "1.0",
                "correlationId": correlation_id or "",
                "sagaId": saga_id or "",
            },
        )
        logger.info(
            "Comando publicado",
            extra={
                "message_type": message_type,
                "topic": topic,
                "saga_id": saga_id,
                "correlation_id": correlation_id,
                "message_id": message_id,
            },
        )
        return message_id

    def close(self) -> None:
        for producer in self._producers.values():
            try:
                producer.close()
            except Exception as exc:
                logger.warning("Error cerrando producer", extra={"error": str(exc)})
        self._producers.clear()
