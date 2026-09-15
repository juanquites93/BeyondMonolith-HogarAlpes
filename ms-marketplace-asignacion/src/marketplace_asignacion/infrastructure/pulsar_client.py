"""Cliente Pulsar compartido."""

import logging
import pulsar

from marketplace_asignacion.infrastructure.config import settings

logger = logging.getLogger(__name__)

_client: pulsar.Client | None = None


def get_pulsar_client() -> pulsar.Client:
    global _client
    if _client is None:
        _client = pulsar.Client(settings.PULSAR_SERVICE_URL)
        logger.info("Pulsar client created", extra={"url": settings.PULSAR_SERVICE_URL})
    return _client


def close_pulsar_client() -> None:
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("Pulsar client closed")
