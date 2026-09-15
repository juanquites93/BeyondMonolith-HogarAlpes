"""Tests de publicación en Pulsar con múltiples tópicos y DLQ."""

import json
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch, call

from marketplace_asignacion.infrastructure.pulsar_producer import (
    PulsarEventProducer,
    _EVENT_TOPIC_MAP,
)
from marketplace_asignacion.infrastructure.orm import OutboxORM, DlqORM
from marketplace_asignacion.infrastructure.config import settings


def test_contrato_mensaje_publicado(db_session):
    db_session.query(OutboxORM).delete()
    db_session.query(DlqORM).delete()
    db_session.commit()

    row = OutboxORM(
        id=str(uuid.uuid4()),
        aggregate_type="Trabajo",
        aggregate_id=str(uuid.uuid4()),
        event_type="ProveedorSeleccionadoParaValidacion",
        version=1,
        payload={"proveedor_id": str(uuid.uuid4()), "trabajo_id": str(uuid.uuid4())},
        occurred_at=datetime.utcnow(),
        correlation_id="corr-abc",
    )
    db_session.add(row)
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
    args, kwargs = mock_producer.send.call_args
    message = json.loads(args[0].decode("utf-8"))

    assert "messageId" in message
    assert message["messageType"] == "ProveedorSeleccionadoParaValidacion"
    assert message["version"] == 1
    assert "occurredAt" in message
    assert message["correlationId"] == "corr-abc"
    assert "idempotencyKey" in message
    assert message["producer"] == "marketplace-asignacion"
    assert "payload" in message
    assert message["payload"]["proveedor_id"] is not None


def test_publicacion_rutea_a_topico_correcto(db_session):
    db_session.query(OutboxORM).delete()
    db_session.query(DlqORM).delete()
    db_session.commit()

    rows = [
        OutboxORM(
            id=str(uuid.uuid4()),
            aggregate_type="Trabajo",
            aggregate_id=str(uuid.uuid4()),
            event_type="GenerarCotizacionCommand",
            version=1,
            payload={"trabajo_id": str(uuid.uuid4())},
            occurred_at=datetime.utcnow(),
            correlation_id="corr-1",
        ),
        OutboxORM(
            id=str(uuid.uuid4()),
            aggregate_type="Trabajo",
            aggregate_id=str(uuid.uuid4()),
            event_type="NotificarProveedorAsignadoCommand",
            version=1,
            payload={"proveedor_id": str(uuid.uuid4())},
            occurred_at=datetime.utcnow(),
            correlation_id="corr-2",
        ),
        OutboxORM(
            id=str(uuid.uuid4()),
            aggregate_type="Trabajo",
            aggregate_id=str(uuid.uuid4()),
            event_type="TrabajoPublicado",
            version=1,
            payload={"trabajo_id": str(uuid.uuid4())},
            occurred_at=datetime.utcnow(),
            correlation_id="corr-3",
        ),
    ]
    for r in rows:
        db_session.add(r)
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

    assert result["published"] == 3
    assert result["dlq"] == 0
    assert mock_producer.send.call_count == 3

    create_calls = mock_client.create_producer.call_args_list
    topics_creados = {c.kwargs.get("topic") or c.args[0] for c in create_calls}
    assert settings.PULSAR_COTIZACIONES_TOPIC in topics_creados
    assert settings.PULSAR_NOTIFICACIONES_TOPIC in topics_creados
    assert settings.PULSAR_PRODUCER_TOPIC in topics_creados


def test_reintentos_en_fallo_de_publicacion(db_session):
    db_session.query(OutboxORM).delete()
    db_session.query(DlqORM).delete()
    db_session.commit()

    row = OutboxORM(
        id=str(uuid.uuid4()),
        aggregate_type="Trabajo",
        aggregate_id=str(uuid.uuid4()),
        event_type="TrabajoPublicado",
        version=1,
        payload={},
        occurred_at=datetime.utcnow(),
        correlation_id="corr-retry",
    )
    db_session.add(row)
    db_session.commit()

    mock_producer = MagicMock()
    mock_producer.send.side_effect = [Exception("timeout"), Exception("timeout"), None]
    mock_client = MagicMock()
    mock_client.create_producer.return_value = mock_producer

    with patch(
        "marketplace_asignacion.infrastructure.pulsar_producer.get_pulsar_client",
        return_value=mock_client,
    ):
        producer = PulsarEventProducer(
            session_factory=lambda: db_session, max_retries=3
        )
        result = producer.publish_pending()

    assert result["published"] == 1
    assert result["dlq"] == 0
    assert mock_producer.send.call_count == 3


def test_mueve_a_dlq_local_si_agota_reintentos(db_session):
    db_session.query(OutboxORM).delete()
    db_session.query(DlqORM).delete()
    db_session.commit()

    row = OutboxORM(
        id=str(uuid.uuid4()),
        aggregate_type="Trabajo",
        aggregate_id=str(uuid.uuid4()),
        event_type="TrabajoPublicado",
        version=1,
        payload={},
        occurred_at=datetime.utcnow(),
        correlation_id="corr-fail",
    )
    db_session.add(row)
    db_session.commit()

    row_id = str(row.id)

    mock_producer = MagicMock()
    mock_producer.send.side_effect = Exception("broker down")
    mock_client = MagicMock()
    mock_client.create_producer.return_value = mock_producer

    with patch(
        "marketplace_asignacion.infrastructure.pulsar_producer.get_pulsar_client",
        return_value=mock_client,
    ):
        producer = PulsarEventProducer(
            session_factory=lambda: db_session, max_retries=2
        )
        result = producer.publish_pending()

    assert result["published"] == 0
    assert result["dlq"] == 1

    # Verificar que el registro fue movido a DLQ
    dlq_entry = db_session.query(DlqORM).filter_by(original_outbox_id=row_id).first()
    assert dlq_entry is not None
    assert dlq_entry.event_type == "TrabajoPublicado"
    assert "broker down" in dlq_entry.error_message

    # Verificar que el outbox fue marcado como procesado para no reintentar más
    outbox_entry = db_session.get(OutboxORM, row_id)
    assert outbox_entry.processed_at is not None


def test_retry_dlq_republica_mensajes_fallidos(db_session):
    db_session.query(OutboxORM).delete()
    db_session.query(DlqORM).delete()
    db_session.commit()

    dlq_row = DlqORM(
        id=str(uuid.uuid4()),
        original_outbox_id=str(uuid.uuid4()),
        aggregate_type="Trabajo",
        aggregate_id=str(uuid.uuid4()),
        event_type="TrabajoPublicado",
        version=1,
        payload={"trabajo_id": str(uuid.uuid4())},
        occurred_at=datetime.utcnow(),
        correlation_id="corr-retry-dlq",
        error_message="timeout",
        failed_at=datetime.utcnow(),
    )
    db_session.add(dlq_row)
    db_session.commit()

    mock_producer = MagicMock()
    mock_client = MagicMock()
    mock_client.create_producer.return_value = mock_producer

    dlq_id = str(dlq_row.id)

    with patch(
        "marketplace_asignacion.infrastructure.pulsar_producer.get_pulsar_client",
        return_value=mock_client,
    ):
        producer = PulsarEventProducer(session_factory=lambda: db_session)
        result = producer.retry_dlq()

    assert result["published"] == 1
    assert mock_producer.send.call_count == 1

    # Verificar que fue marcado como reprocessado
    fresh = db_session.get(DlqORM, dlq_id)
    assert fresh.reprocessed_at is not None
