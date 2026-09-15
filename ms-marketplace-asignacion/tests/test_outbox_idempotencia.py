"""Tests de idempotencia en publicación desde Outbox."""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

from marketplace_asignacion.infrastructure.pulsar_producer import PulsarEventProducer
from marketplace_asignacion.infrastructure.orm import OutboxORM, DlqORM


def test_outbox_no_publica_registros_ya_procesados(db_session):
    db_session.query(OutboxORM).delete()
    db_session.query(DlqORM).delete()
    db_session.commit()

    # Un registro ya procesado
    procesado = OutboxORM(
        id=str(uuid.uuid4()),
        aggregate_type="Trabajo",
        aggregate_id=str(uuid.uuid4()),
        event_type="TrabajoPublicado",
        version=1,
        payload={},
        occurred_at=datetime.utcnow(),
        correlation_id="corr-old",
        processed_at=datetime.utcnow(),
    )
    # Un registro pendiente
    pendiente = OutboxORM(
        id=str(uuid.uuid4()),
        aggregate_type="Trabajo",
        aggregate_id=str(uuid.uuid4()),
        event_type="TrabajoPublicado",
        version=1,
        payload={},
        occurred_at=datetime.utcnow(),
        correlation_id="corr-new",
    )
    db_session.add_all([procesado, pendiente])
    db_session.commit()

    mock_producer = MagicMock()
    mock_client = MagicMock()
    mock_client.create_producer.return_value = mock_producer

    with patch(
        "marketplace_asignacion.infrastructure.pulsar_producer.get_pulsar_client",
        return_value=mock_client,
    ):
        producer = PulsarEventProducer(session_factory=lambda: db_session)
        result = producer.publish_pending()

    assert result["published"] == 1
    assert result["dlq"] == 0
    assert mock_producer.send.call_count == 1
