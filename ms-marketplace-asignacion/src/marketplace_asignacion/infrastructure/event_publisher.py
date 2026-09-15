"""Publicador de eventos: delega en PulsarEventProducer."""

from __future__ import annotations
import logging

from marketplace_asignacion.infrastructure.pulsar_producer import PulsarEventProducer

logger = logging.getLogger(__name__)


class EventPublisher(PulsarEventProducer):
    """Alias hacia PulsarEventProducer para mantener compatibilidad."""

    pass
