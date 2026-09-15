"""Test de idempotencia."""

import uuid

from verificacion_acreditacion.infrastructure.idempotency import IdempotencyService
from verificacion_acreditacion.application.commands import IniciarVerificacionProveedor
from verificacion_acreditacion.application.handlers import CommandHandler
from verificacion_acreditacion.infrastructure.unit_of_work_impl import (
    SqlAlchemyUnitOfWork,
)
from verificacion_acreditacion.infrastructure.outbox import SqlAlchemyOutboxStore
from verificacion_acreditacion.infrastructure.orm import IdempotencyKeyORM, OutboxORM


def test_comando_duplicado_no_duplica_resultado(session):
    idempotency = IdempotencyService(session)
    key = "idem-key-123"

    calls = []

    def _run():
        calls.append(1)
        uow = SqlAlchemyUnitOfWork(session_factory=lambda: session)
        outbox = SqlAlchemyOutboxStore()
        handler = CommandHandler(uow, outbox)
        cmd = IniciarVerificacionProveedor(proveedor_id=uuid.uuid4())
        with uow:
            outbox.bind(uow.session)
            return handler.handle_iniciar_verificacion(cmd)

    result1 = idempotency.check_or_run(key, "IniciarVerificacionProveedor", _run)
    result2 = idempotency.check_or_run(key, "IniciarVerificacionProveedor", _run)

    assert len(calls) == 1
    # La primera vez retorna el objeto; la segunda el dict cacheado
    pid1 = str(result1.id if hasattr(result1, "id") else result1["proveedor_id"])
    pid2 = str(result2.id if hasattr(result2, "id") else result2["proveedor_id"])
    assert pid1 == pid2

    keys = session.query(IdempotencyKeyORM).all()
    assert len(keys) == 1
