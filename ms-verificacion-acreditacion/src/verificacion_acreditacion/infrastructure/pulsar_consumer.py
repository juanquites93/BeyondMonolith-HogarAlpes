"""Consumidor Pulsar para comandos de integración."""

from __future__ import annotations
import json
import logging
import uuid
from typing import Callable

import pulsar

from verificacion_acreditacion.infrastructure.config import settings
from verificacion_acreditacion.infrastructure.pulsar_client import get_pulsar_client

logger = logging.getLogger(__name__)


class PulsarCommandConsumer:
    """Consume comandos desde Pulsar y los enruta a un handler.

    Configura Dead Letter Policy para que mensajes que fallen repetidamente
    se muevan automáticamente al tópico DLQ.
    """

    def __init__(self, handler: Callable[[dict], None]):
        self._handler = handler
        self._consumer: pulsar.Consumer | None = None
        self._running = False

    def start(self) -> None:
        client = get_pulsar_client()
        topics = [t.strip() for t in settings.PULSAR_CONSUMER_TOPICS.split(",")]
        self._consumer = client.subscribe(
            topic=topics,
            subscription_name=settings.PULSAR_SUBSCRIPTION,
            consumer_type=pulsar.ConsumerType.Shared,
            dead_letter_policy=pulsar.ConsumerDeadLetterPolicy(
                max_redeliver_count=settings.PULSAR_MAX_REDELIVER_COUNT,
                dead_letter_topic=settings.PULSAR_DLQ_TOPIC,
            ),
        )
        self._running = True
        logger.info(
            "Pulsar consumer started",
            extra={
                "topics": topics,
                "dlq_topic": settings.PULSAR_DLQ_TOPIC,
                "max_redeliver": settings.PULSAR_MAX_REDELIVER_COUNT,
            },
        )
        while self._running:
            try:
                msg = self._consumer.receive(timeout_millis=5000)
            except pulsar.Timeout:
                continue
            except Exception as exc:
                logger.warning("Error recibiendo mensaje", extra={"error": str(exc)})
                continue

            try:
                data = json.loads(msg.data().decode("utf-8"))
                self._handler(data)
                self._consumer.acknowledge(msg)
                logger.info(
                    "Mensaje procesado",
                    extra={
                        "message_id": str(msg.message_id()),
                        "type": data.get("messageType"),
                    },
                )
            except Exception as exc:
                logger.error(
                    "Error procesando mensaje; enviando a DLQ (nack)",
                    extra={"error": str(exc), "message_id": str(msg.message_id())},
                )
                self._consumer.negative_acknowledge(msg)

    def stop(self) -> None:
        self._running = False
        if self._consumer:
            self._consumer.close()
            logger.info("Pulsar consumer stopped")
