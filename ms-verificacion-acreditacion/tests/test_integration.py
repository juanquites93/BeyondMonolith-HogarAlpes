"""Tests de integración API -> DB -> outbox."""

import uuid

from verificacion_acreditacion.application.commands import IniciarVerificacionProveedor
from verificacion_acreditacion.application.handlers import CommandHandler
from verificacion_acreditacion.infrastructure.unit_of_work_impl import (
    SqlAlchemyUnitOfWork,
)
from verificacion_acreditacion.infrastructure.outbox import SqlAlchemyOutboxStore
from verificacion_acreditacion.infrastructure.repositories import (
    SqlAlchemyProveedorRepository,
)
from verificacion_acreditacion.infrastructure.orm import OutboxORM
from verificacion_acreditacion.infrastructure.fake_external_validation_adapter import (
    FakeExternalValidationAdapter,
)


def test_iniciar_verificacion_persiste_y_genera_outbox(session):
    uow = SqlAlchemyUnitOfWork(session_factory=lambda: session)
    outbox = SqlAlchemyOutboxStore()
    handler = CommandHandler(uow, outbox)

    proveedor_id = uuid.uuid4()
    cmd = IniciarVerificacionProveedor(proveedor_id=proveedor_id)

    with uow:
        outbox.bind(uow.session)
        proveedor = handler.handle_iniciar_verificacion(cmd)

    # Verificar persistencia: la dependencia externa está disponible por defecto,
    # por lo que el flujo completo inicia, aprueba y acredita en un solo paso.
    repo = SqlAlchemyProveedorRepository(session)
    p = repo.get(proveedor_id)
    assert p is not None
    assert p.estado_verificacion.value == "APROBADA"
    assert p.estado_acreditacion.value == "ACREDITADO"

    # Verificar outbox
    rows = session.query(OutboxORM).all()
    event_types = [r.event_type for r in rows]
    assert "VerificacionProveedorIniciada" in event_types
    assert "VerificacionProveedorAprobada" in event_types
    assert "ProveedorAcreditado" in event_types


def test_iniciar_verificacion_dependencia_caida_emite_pendiente(session):
    FakeExternalValidationAdapter.marcar_caida()
    try:
        uow = SqlAlchemyUnitOfWork(session_factory=lambda: session)
        outbox = SqlAlchemyOutboxStore()
        handler = CommandHandler(uow, outbox)

        proveedor_id = uuid.uuid4()
        trabajo_id = str(uuid.uuid4())
        cmd = IniciarVerificacionProveedor(
            proveedor_id=proveedor_id, trabajo_id=trabajo_id
        )

        with uow:
            outbox.bind(uow.session)
            handler.handle_iniciar_verificacion(cmd)

        repo = SqlAlchemyProveedorRepository(session)
        p = repo.get(proveedor_id)
        assert p is not None
        assert p.estado_verificacion.value == "PENDIENTE"

        rows = session.query(OutboxORM).all()
        event_types = [r.event_type for r in rows]
        assert "VerificacionPendiente" in event_types
        pendiente = [r for r in rows if r.event_type == "VerificacionPendiente"][0]
        assert pendiente.payload["trabajo_id"] == trabajo_id
        assert "no disponible" in pendiente.payload["motivo"]
    finally:
        FakeExternalValidationAdapter.marcar_disponible()
