from __future__ import annotations
import json
import logging
import threading

from notificaciones.application.commands import (
    NotificarProveedorAsignado,
    NotificarClienteProveedorAsignado,
)
from notificaciones.application.handlers import CommandHandler
from notificaciones.infrastructure import database as db_module
from notificaciones.infrastructure.config import settings
from notificaciones.infrastructure.idempotency import IdempotencyService
from notificaciones.infrastructure.outbox import SqlAlchemyOutboxStore
from notificaciones.infrastructure.pasarela_adapter import PasarelaSimulada
from notificaciones.infrastructure.unit_of_work_impl import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)

_pasarela = PasarelaSimulada()


def procesar_mensaje(datos: bytes) -> None:
    """Traduce el sobre JSON del comando entrante y ejecuta el manejador.

    Tópico único `notificaciones.comandos`, `messageType` discrimina entre
    los comandos que llegan (ver docs/CONTRATO_EVENTOS.md).
    """
    sobre = json.loads(datos)
    tipo = sobre.get("messageType")
    payload = sobre.get("payload", {})
    correlation_id = sobre.get("correlationId")
    idempotency_key = sobre.get("idempotencyKey") or sobre.get("messageId")

    uow = SqlAlchemyUnitOfWork()
    outbox = SqlAlchemyOutboxStore()
    handler = CommandHandler(uow, outbox, _pasarela)

    def _run():
        with uow:
            outbox.bind(uow.session)
            if tipo == "NotificarProveedorAsignadoCommand":
                detalles = payload.get("detalles_trabajo") or {}
                ubicacion = detalles.get("ubicacion") or {}
                cmd = NotificarProveedorAsignado(
                    proveedor_id=payload["proveedor_id"],
                    trabajo_id=payload["trabajo_id"],
                    cliente_id=payload["cliente_id"],
                    descripcion=detalles.get("descripcion", ""),
                    categoria=detalles.get("categoria", ""),
                    direccion=ubicacion.get("direccion", ""),
                    ciudad=ubicacion.get("ciudad", ""),
                    correlation_id=correlation_id,
                )
                return handler.handle_notificar_proveedor_asignado(cmd)
            if tipo == "NotificarClienteProveedorAsignadoCommand":
                cmd = NotificarClienteProveedorAsignado(
                    cliente_id=payload["cliente_id"],
                    trabajo_id=payload["trabajo_id"],
                    proveedor_id=payload["proveedor_id"],
                    correlation_id=correlation_id,
                )
                return handler.handle_notificar_cliente_proveedor_asignado(cmd)
            logger.warning("messageType desconocido: %s (mensaje descartado)", tipo)
            return None

    session_idem = db_module.SessionLocal()
    try:
        idempotencia = IdempotencyService(session_idem)
        if idempotency_key:
            idempotencia.check_or_run(idempotency_key, tipo or "desconocido", _run)
        else:
            _run()
    finally:
        session_idem.close()

    from notificaciones.infrastructure.event_publisher import SimulatedEventPublisher

    SimulatedEventPublisher(db_module.SessionLocal).publish_pending()


def iniciar_consumidor_en_hilo() -> threading.Thread | None:
    """Arranca el consumo de `TOPICO_COMANDOS` en un hilo de fondo.

    Solo si `PULSAR_SERVICE_URL` esta configurado: el cluster lo despliega el
    equipo en otro punto, este servicio solo debe estar preparado para
    conectarse cuando exista.
    """
    if not settings.PULSAR_SERVICE_URL:
        logger.warning(
            "PULSAR_SERVICE_URL vacio: el servicio arranca sin consumir comandos, "
            "solo sirve queries HTTP."
        )
        return None

    import pulsar

    def _bucle() -> None:
        client = pulsar.Client(settings.PULSAR_SERVICE_URL)
        consumidor = client.subscribe(
            settings.TOPICO_COMANDOS,
            subscription_name=settings.PULSAR_SUSCRIPCION,
            consumer_type=pulsar.ConsumerType.Shared,
        )
        while True:
            mensaje = consumidor.receive()
            try:
                procesar_mensaje(mensaje.data())
                consumidor.acknowledge(mensaje)
            except Exception:
                logger.exception("Fallo procesando un comando; se hace nack.")
                consumidor.negative_acknowledge(mensaje)

    hilo = threading.Thread(target=_bucle, name="consumidor-pulsar", daemon=True)
    hilo.start()
    return hilo
