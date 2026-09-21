"""Tests del orquestador de Sagas."""

from unittest.mock import Mock, patch

import pytest

from ms_orquestador.application.orchestrator import SagaOrchestrator
from ms_orquestador.application.saga_state import SagaState
from ms_orquestador.infrastructure.saga_repository import SagaRepository


@pytest.fixture
def producer():
    mock = Mock()
    mock.send_command = Mock(return_value="msg-id")
    return mock


@pytest.fixture
def orchestrator(session_factory, producer):
    return SagaOrchestrator(
        session_factory=session_factory,
        producer=producer,
        max_retries=2,
        retry_delay_seconds=0,
    )


def test_happy_path_crea_saga_y_avanza_estados(orchestrator, session_factory):
    event = {
        "messageId": "evt-1",
        "messageType": "ProveedorSeleccionado",
        "correlationId": "corr-1",
        "causationId": None,
        "idempotencyKey": "evt-1",
        "producer": "marketplace-asignacion",
        "payload": {
            "trabajo_id": "trab-1",
            "proveedor_id": "prov-1",
            "cliente_id": "cli-1",
            "alcance": {"descripcion": "Pintura", "categoria": "Pintura"},
            "ubicacion": {"direccion": "Calle 1", "ciudad": "Bogotá"},
        },
    }
    orchestrator.handle_event(event)

    session = session_factory()
    saga = SagaRepository(session).get_by_trabajo("trab-1")
    assert saga is not None
    assert saga.current_state == SagaState.VERIFICACION_EN_PROCESO.value

    orchestrator.handle_event(
        {
            "messageId": "evt-2",
            "messageType": "ProveedorAcreditado",
            "sagaId": saga.saga_id,
            "correlationId": saga.correlation_id,
            "causationId": "msg-1",
            "idempotencyKey": "evt-2",
            "producer": "verificacion-acreditacion",
            "payload": {"proveedor_id": "prov-1"},
        }
    )
    saga = SagaRepository(session).get(saga.saga_id)
    assert saga.current_state == SagaState.COTIZACION_EN_PROCESO.value

    orchestrator.handle_event(
        {
            "messageId": "evt-3",
            "messageType": "CotizacionSolicitada",
            "sagaId": saga.saga_id,
            "correlationId": saga.correlation_id,
            "causationId": "msg-2",
            "idempotencyKey": "evt-3",
            "producer": "generador-cotizacion",
            "payload": {"trabajo_id": "trab-1", "cotizacion_id": "cot-1"},
        }
    )
    saga = SagaRepository(session).get(saga.saga_id)
    assert saga.current_state == SagaState.NOTIFICACION_EN_PROCESO.value

    orchestrator.handle_event(
        {
            "messageId": "evt-4",
            "messageType": "NotificacionEnviada",
            "sagaId": saga.saga_id,
            "correlationId": saga.correlation_id,
            "causationId": "msg-3",
            "idempotencyKey": "evt-4",
            "producer": "ms-notificaciones",
            "payload": {"notificacion_id": "not-1"},
        }
    )
    saga = SagaRepository(session).get(saga.saga_id)
    assert saga.current_state == SagaState.COMPLETADA.value


def test_verificacion_pendiente_reintenta_y_falla(orchestrator, session_factory):
    event = {
        "messageId": "evt-1",
        "messageType": "ProveedorSeleccionado",
        "correlationId": "corr-r",
        "causationId": None,
        "idempotencyKey": "evt-1",
        "producer": "marketplace-asignacion",
        "payload": {
            "trabajo_id": "trab-r",
            "proveedor_id": "prov-r",
            "cliente_id": "cli-r",
        },
    }
    orchestrator.handle_event(event)
    session = session_factory()
    saga = SagaRepository(session).get_by_trabajo("trab-r")

    def pending(mid):
        return {
            "messageId": mid,
            "messageType": "VerificacionPendiente",
            "sagaId": saga.saga_id,
            "correlationId": saga.correlation_id,
            "causationId": "msg-1",
            "idempotencyKey": mid,
            "producer": "verificacion-acreditacion",
            "payload": {"motivo": "servicio externo no disponible"},
        }

    orchestrator.handle_event(pending("evt-p1"))
    saga = SagaRepository(session).get(saga.saga_id)
    assert saga.current_state == SagaState.ESPERANDO_REINTENTO.value

    orchestrator.process_retries()
    saga = SagaRepository(session).get(saga.saga_id)
    assert saga.retry_count == 1

    orchestrator.handle_event(pending("evt-p2"))
    orchestrator.process_retries()
    saga = SagaRepository(session).get(saga.saga_id)
    assert saga.retry_count == 2

    orchestrator.handle_event(pending("evt-p3"))
    orchestrator.process_retries()
    saga = SagaRepository(session).get(saga.saga_id)
    assert saga.current_state == SagaState.FALLIDA.value


def test_idempotencia_no_crea_sagas_duplicadas(orchestrator, session_factory):
    event = {
        "messageId": "evt-1",
        "messageType": "ProveedorSeleccionado",
        "correlationId": "corr-i",
        "causationId": None,
        "idempotencyKey": "evt-1",
        "producer": "marketplace-asignacion",
        "payload": {
            "trabajo_id": "trab-i",
            "proveedor_id": "prov-i",
            "cliente_id": "cli-i",
        },
    }
    orchestrator.handle_event(event)
    orchestrator.handle_event(event)

    session = session_factory()
    from ms_orquestador.infrastructure.orm import SagaORM

    count = session.query(SagaORM).filter_by(trabajo_id="trab-i").count()
    assert count == 1


def test_notificacion_fallida_dispara_compensacion(
    orchestrator, session_factory, producer
):
    # Happy path hasta NOTIFICACION_EN_PROCESO
    event = {
        "messageId": "evt-1",
        "messageType": "ProveedorSeleccionado",
        "correlationId": "corr-c",
        "causationId": None,
        "idempotencyKey": "evt-1",
        "producer": "marketplace-asignacion",
        "payload": {
            "trabajo_id": "trab-c",
            "proveedor_id": "prov-c",
            "cliente_id": "cli-c",
        },
    }
    orchestrator.handle_event(event)
    session = session_factory()
    saga = SagaRepository(session).get_by_trabajo("trab-c")

    orchestrator.handle_event(
        {
            "messageId": "evt-2",
            "messageType": "ProveedorAcreditado",
            "sagaId": saga.saga_id,
            "correlationId": saga.correlation_id,
            "causationId": "msg-1",
            "idempotencyKey": "evt-2",
            "producer": "verificacion-acreditacion",
            "payload": {
                "proveedor_id": "prov-c",
                "acreditacion_id": "acr-1",
            },
        }
    )
    saga = SagaRepository(session).get(saga.saga_id)
    assert saga.current_state == SagaState.COTIZACION_EN_PROCESO.value

    orchestrator.handle_event(
        {
            "messageId": "evt-3",
            "messageType": "CotizacionSolicitada",
            "sagaId": saga.saga_id,
            "correlationId": saga.correlation_id,
            "causationId": "msg-2",
            "idempotencyKey": "evt-3",
            "producer": "generador-cotizacion",
            "payload": {"trabajo_id": "trab-c", "cotizacion_id": "cot-1"},
        }
    )
    saga = SagaRepository(session).get(saga.saga_id)
    assert saga.current_state == SagaState.NOTIFICACION_EN_PROCESO.value

    # Simular respuesta HTTP exitosa de marketplace al revertir selección
    with patch("ms_orquestador.application.orchestrator.requests.post") as mock_post:
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        orchestrator.handle_event(
            {
                "messageId": "evt-4",
                "messageType": "NotificacionFallida",
                "sagaId": saga.saga_id,
                "correlationId": saga.correlation_id,
                "causationId": "msg-3",
                "idempotencyKey": "evt-4",
                "producer": "ms-notificaciones",
                "payload": {
                    "trabajo_id": "trab-c",
                    "motivo": "pasarela no acepto el envio",
                },
            }
        )

        # Simular que cotización confirma la cancelación
        orchestrator.handle_event(
            {
                "messageId": "evt-5",
                "messageType": "CotizacionCancelada",
                "sagaId": saga.saga_id,
                "correlationId": saga.correlation_id,
                "causationId": "msg-4",
                "idempotencyKey": "evt-5",
                "producer": "generador-cotizacion",
                "payload": {"trabajo_id": "trab-c", "cotizacion_id": "cot-1"},
            }
        )

        # Simular que verificación confirma la revocación de acreditación
        orchestrator.handle_event(
            {
                "messageId": "evt-6",
                "messageType": "AcreditacionRevocada",
                "sagaId": saga.saga_id,
                "correlationId": saga.correlation_id,
                "causationId": "msg-5",
                "idempotencyKey": "evt-6",
                "producer": "verificacion-acreditacion",
                "payload": {"proveedor_id": "prov-c", "acreditacion_id": "acr-1"},
            }
        )

    saga = SagaRepository(session).get(saga.saga_id)
    assert saga.current_state == SagaState.COMPENSADA.value
    assert "CotizacionCancelada" in saga.compensated_steps
    assert "AcreditacionRevocada" in saga.compensated_steps
    assert "SeleccionProveedorRevertida" in saga.compensated_steps

    # Verificar que se enviaron los comandos de compensación
    sent_types = [
        call.kwargs["message_type"] for call in producer.send_command.call_args_list
    ]
    assert "CancelarCotizacionCommand" in sent_types
    assert "RevocarAcreditacionProveedorCommand" in sent_types
    mock_post.assert_called_once()
