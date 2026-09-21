"""Adaptador de mensajería: consume comandos de Pulsar y los convierte a comandos de app."""

from __future__ import annotations
import uuid
import logging

from verificacion_acreditacion.application.commands import (
    IniciarVerificacionProveedor,
    AcreditarProveedor,
    RevocarAcreditacionProveedor,
)
from verificacion_acreditacion.application.handlers import CommandHandler
from verificacion_acreditacion.application.external_validation_port import (
    ExternalValidationPort,
)
from verificacion_acreditacion.infrastructure.unit_of_work_impl import (
    SqlAlchemyUnitOfWork,
)
from verificacion_acreditacion.infrastructure.outbox import SqlAlchemyOutboxStore
from verificacion_acreditacion.infrastructure.fake_external_validation_adapter import (
    FakeExternalValidationAdapter,
)

logger = logging.getLogger(__name__)


def handle_incoming_message(
    data: dict, external_validation: ExternalValidationPort = None
) -> None:
    """Procesa un mensaje recibido de Pulsar."""
    message_type = data.get("messageType")
    payload = data.get("payload", {})
    correlation_id = data.get("correlationId")
    idempotency_key = data.get("idempotencyKey")

    logger.info(
        "Procesando mensaje entrante",
        extra={"message_type": message_type, "correlation_id": correlation_id},
    )

    if external_validation is None:
        external_validation = FakeExternalValidationAdapter()

    uow = SqlAlchemyUnitOfWork()
    outbox = SqlAlchemyOutboxStore()
    handler = CommandHandler(uow, outbox, external_validation)

    with uow:
        outbox.bind(uow.session)
        if message_type == "ProveedorSeleccionadoParaValidacion":
            proveedor_id = uuid.UUID(payload.get("proveedor_id"))
            trabajo_id = payload.get("trabajo_id")
            cmd = IniciarVerificacionProveedor(
                proveedor_id=proveedor_id,
                trabajo_id=trabajo_id,
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
            )
            handler.handle_iniciar_verificacion(cmd)
        elif message_type == "ValidarAcreditacionProveedorCommand":
            proveedor_id = uuid.UUID(payload.get("proveedor_id"))
            cmd = AcreditarProveedor(
                proveedor_id=proveedor_id,
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
            )
            handler.handle_acreditar_proveedor(cmd)
        elif message_type == "RevocarAcreditacionProveedorCommand":
            proveedor_id = uuid.UUID(payload.get("proveedor_id"))
            acreditacion_id = payload.get("acreditacion_id")
            cmd = RevocarAcreditacionProveedor(
                proveedor_id=proveedor_id,
                acreditacion_id=uuid.UUID(acreditacion_id) if acreditacion_id else None,
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
            )
            handler.handle_revocar_acreditacion(cmd)
        else:
            logger.warning(
                "Tipo de mensaje no soportado", extra={"message_type": message_type}
            )
            return
