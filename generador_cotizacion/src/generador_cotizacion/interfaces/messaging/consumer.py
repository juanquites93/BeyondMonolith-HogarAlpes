"""Adaptador de mensajería: consume comandos de Pulsar y los convierte a comandos de app."""

from __future__ import annotations
import uuid
import logging

from generador_cotizacion.application.commands import (
    GenerarCotizacion,
    CancelarCotizacion,
)
from generador_cotizacion.application.handlers import CommandHandler
from generador_cotizacion.infrastructure import database as db_module
from generador_cotizacion.infrastructure.unit_of_work_impl import SqlAlchemyUnitOfWork
from generador_cotizacion.infrastructure.outbox import SqlAlchemyOutboxStore
from generador_cotizacion.infrastructure.idempotency import IdempotencyService

logger = logging.getLogger(__name__)


def handle_incoming_message(data: dict) -> None:
    """Procesa un mensaje recibido de Pulsar.

    Soporta `GenerarCotizacionCommand` y `CancelarCotizacionCommand`.
    """
    message_type = data.get("messageType")
    payload = data.get("payload") or {}
    correlation_id = data.get("correlationId")
    idempotency_key = data.get("idempotencyKey") or data.get("messageId")

    logger.info(
        "Procesando mensaje entrante",
        extra={"message_type": message_type, "correlation_id": correlation_id},
    )

    db = db_module.SessionLocal()
    try:
        idempotency = IdempotencyService(db)

        if message_type == "GenerarCotizacionCommand":

            def _run_generar():
                trabajo_id = uuid.UUID(payload["trabajo_id"])
                alcance = payload.get("alcance") or {}
                descripcion = alcance.get("descripcion") or ""

                uow = SqlAlchemyUnitOfWork()
                outbox = SqlAlchemyOutboxStore()
                handler = CommandHandler(uow, outbox)
                cmd = GenerarCotizacion(
                    trabajo_id=trabajo_id,
                    descripcion=descripcion,
                    correlation_id=correlation_id,
                    idempotency_key=idempotency_key,
                )
                with uow:
                    outbox.bind(uow.session)
                    cotizacion = handler.handle_generar_cotizacion(cmd)
                cotizacion.limpiar_eventos()
                return cotizacion

            key = idempotency_key or IdempotencyService.compute_key(
                message_type, payload, correlation_id
            )
            idempotency.check_or_run(key, message_type, _run_generar)

        elif message_type == "CancelarCotizacionCommand":

            def _run_cancelar():
                cotizacion_id = uuid.UUID(payload["cotizacion_id"])

                uow = SqlAlchemyUnitOfWork()
                outbox = SqlAlchemyOutboxStore()
                handler = CommandHandler(uow, outbox)
                cmd = CancelarCotizacion(
                    cotizacion_id=cotizacion_id,
                    correlation_id=correlation_id,
                    idempotency_key=idempotency_key,
                )
                with uow:
                    outbox.bind(uow.session)
                    cotizacion = handler.handle_cancelar_cotizacion(cmd)
                cotizacion.limpiar_eventos()
                return cotizacion

            key = idempotency_key or IdempotencyService.compute_key(
                message_type, payload, correlation_id
            )
            idempotency.check_or_run(key, message_type, _run_cancelar)

        else:
            logger.warning(
                "Tipo de mensaje no soportado", extra={"message_type": message_type}
            )
    finally:
        db.close()
