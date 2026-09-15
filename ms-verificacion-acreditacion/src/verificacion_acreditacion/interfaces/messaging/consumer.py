"""Adaptador de mensajería: consume comandos de Pulsar y los convierte a comandos de app."""

from __future__ import annotations
import uuid
import logging

from verificacion_acreditacion.application.commands import (
    IniciarVerificacionProveedor,
    AcreditarProveedor,
)
from verificacion_acreditacion.application.handlers import CommandHandler
from verificacion_acreditacion.infrastructure.unit_of_work_impl import (
    SqlAlchemyUnitOfWork,
)
from verificacion_acreditacion.infrastructure.outbox import SqlAlchemyOutboxStore

logger = logging.getLogger(__name__)


def handle_incoming_message(data: dict) -> None:
    """Procesa un mensaje recibido de Pulsar."""
    message_type = data.get("messageType")
    payload = data.get("payload", {})
    correlation_id = data.get("correlationId")
    idempotency_key = data.get("idempotencyKey")

    logger.info(
        "Procesando mensaje entrante",
        extra={"message_type": message_type, "correlation_id": correlation_id},
    )

    uow = SqlAlchemyUnitOfWork()
    outbox = SqlAlchemyOutboxStore()
    handler = CommandHandler(uow, outbox)

    with uow:
        outbox.bind(uow.session)
        if message_type == "ProveedorSeleccionadoParaValidacion":
            proveedor_id = uuid.UUID(payload.get("proveedor_id"))
            cmd = IniciarVerificacionProveedor(
                proveedor_id=proveedor_id,
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
        else:
            logger.warning(
                "Tipo de mensaje no soportado", extra={"message_type": message_type}
            )
            return
