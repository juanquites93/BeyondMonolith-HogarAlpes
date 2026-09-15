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


def test_iniciar_verificacion_persiste_y_genera_outbox(session):
    uow = SqlAlchemyUnitOfWork(session_factory=lambda: session)
    outbox = SqlAlchemyOutboxStore()
    handler = CommandHandler(uow, outbox)

    proveedor_id = uuid.uuid4()
    cmd = IniciarVerificacionProveedor(proveedor_id=proveedor_id)

    with uow:
        outbox.bind(uow.session)
        proveedor = handler.handle_iniciar_verificacion(cmd)

    # Verificar persistencia
    repo = SqlAlchemyProveedorRepository(session)
    p = repo.get(proveedor_id)
    assert p is not None
    assert p.estado_verificacion.value == "PENDIENTE"

    # Verificar outbox
    rows = session.query(OutboxORM).all()
    assert len(rows) == 1
    assert rows[0].event_type == "VerificacionProveedorIniciada"
