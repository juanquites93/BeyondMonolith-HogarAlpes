"""Consumidor Pulsar del orquestador.

Escucha eventos de los microservicios participantes y los entrega al
orquestador para que avance la Saga.
"""

from __future__ import annotations
import json
import logging
from typing import Callable, List

import pulsar

from ms_orquestador.infrastructure.config import settings
from ms_orquestador.infrastructure.pulsar_client import get_pulsar_client

logger = logging.getLogger(__name__)


class PulsarEventConsumer:
    """Consume eventos de Pulsar y los enruta al orquestador.

    Se suscribe a múltiples tópicos de eventos. Usa Dead Letter Policy para
    mensajes que fallan repetidamente.
    """

    def __init__(self, handler: Callable[[dict], None]):
        self._handler = handler
        self._consumer: pulsar.Consumer | None = None
        self._running = False

    def start(self) -> None:
        topics: List[str] = [
            settings.PULSAR_EVENTOS_MARKETPLACE,
            settings.PULSAR_EVENTOS_VERIFICACION,
            settings.PULSAR_EVENTOS_COTIZACION,
            settings.PULSAR_EVENTOS_NOTIFICACION,
        ]
        client = get_pulsar_client()
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
            "Pulsar consumer iniciado",
            extra={
                "topics": topics,
                "subscription": settings.PULSAR_SUBSCRIPTION,
                "dlq_topic": settings.PULSAR_DLQ_TOPIC,
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
                    "Evento procesado",
                    extra={
                        "message_id": str(msg.message_id()),
                        "type": data.get("messageType"),
                        "saga_id": data.get("sagaId"),
                    },
                )
            except Exception as exc:
                logger.error(
                    "Error procesando evento; enviando a DLQ (nack)",
                    extra={
                        "error": str(exc),
                        "message_id": str(msg.message_id()),
                        "type": data.get("messageType"),
                    },
                )
                self._consumer.negative_acknowledge(msg)

    def stop(self) -> None:
        self._running = False
        if self._consumer:
            self._consumer.close()
            logger.info("Pulsar consumer detenido")
