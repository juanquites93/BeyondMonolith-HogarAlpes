"""Test de consumer Pulsar procesando evento entrante."""

import uuid

from verificacion_acreditacion.interfaces.messaging.consumer import (
    handle_incoming_message,
)
from verificacion_acreditacion.infrastructure.database import SessionLocal
from verificacion_acreditacion.infrastructure.repositories import (
    SqlAlchemyProveedorRepository,
)
from verificacion_acreditacion.infrastructure.orm import OutboxORM


def test_consumer_procesa_proveedor_seleccionado(session):
    # Simulamos base compartida (en test usamos la misma sesión)
    proveedor_id = uuid.uuid4()
    message = {
        "messageType": "ProveedorSeleccionadoParaValidacion",
        "correlationId": str(uuid.uuid4()),
        "idempotencyKey": str(uuid.uuid4()),
        "payload": {
            "proveedor_id": str(proveedor_id),
        },
    }

    # Usamos la sesión in-memory
    from verificacion_acreditacion.infrastructure.unit_of_work_impl import (
        SqlAlchemyUnitOfWork,
    )
    from verificacion_acreditacion.infrastructure.outbox import SqlAlchemyOutboxStore
    from verificacion_acreditacion.application.handlers import CommandHandler

    uow = SqlAlchemyUnitOfWork(session_factory=lambda: session)
    outbox = SqlAlchemyOutboxStore()
    handler = CommandHandler(uow, outbox)

    with uow:
        outbox.bind(uow.session)
        if message["messageType"] == "ProveedorSeleccionadoParaValidacion":
            from verificacion_acreditacion.application.commands import (
                IniciarVerificacionProveedor,
            )

            cmd = IniciarVerificacionProveedor(
                proveedor_id=proveedor_id,
                correlation_id=message.get("correlationId"),
                idempotency_key=message.get("idempotencyKey"),
            )
            handler.handle_iniciar_verificacion(cmd)

    repo = SqlAlchemyProveedorRepository(session)
    p = repo.get(proveedor_id)
    assert p is not None
    assert p.estado_verificacion.value == "PENDIENTE"

    rows = session.query(OutboxORM).all()
    assert len(rows) == 1
    assert rows[0].event_type == "VerificacionProveedorIniciada"
