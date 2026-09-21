"""Cliente Pulsar compartido para el orquestador."""

from __future__ import annotations
import logging
import threading

import pulsar

from ms_orquestador.infrastructure.config import settings

logger = logging.getLogger(__name__)

_client: pulsar.Client | None = None
_lock = threading.Lock()


def get_pulsar_client() -> pulsar.Client:
    global _client
    with _lock:
        if _client is None:
            _client = pulsar.Client(settings.PULSAR_SERVICE_URL)
            logger.info(
                "Pulsar client creado",
                extra={"service_url": settings.PULSAR_SERVICE_URL},
            )
        return _client


def close_pulsar_client() -> None:
    global _client
    with _lock:
        if _client is not None:
            _client.close()
            _client = None
            logger.info("Pulsar client cerrado")
