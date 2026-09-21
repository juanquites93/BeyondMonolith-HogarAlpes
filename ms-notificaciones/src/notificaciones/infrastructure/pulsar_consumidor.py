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
from notificaciones.infrastructure.metrics import eventos_consumidos_total
from notificaciones.infrastructure.outbox import SqlAlchemyOutboxStore
from notificaciones.infrastructure.pasarela_adapter import PasarelaSimulada
from notificaciones.infrastructure.unit_of_work_impl import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)

_pasarela = PasarelaSimulada()

# Bandera compartida: True mientras el hilo de abajo esta conectado y
# suscrito a Pulsar. La lee el endpoint /ready para saber si esta replica
# puede atender trafico real (no cambia nada del procesamiento de mensajes).
_consumidor_pulsar_activo = False


def consumidor_esta_listo() -> bool:
    """True si no hace falta Pulsar (PULSAR_SERVICE_URL vacio) o si el
    consumidor sigue conectado y suscrito."""
    if not settings.PULSAR_SERVICE_URL:
        return True
    return _consumidor_pulsar_activo


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

    if not idempotency_key:
        # El sobre no trae idempotencyKey ni messageId: se deriva una clave
        # del propio contenido del comando, para no quedar sin proteccion
        # contra duplicados (dos entregas del mismo mensaje producen el
        # mismo hash y la segunda se detecta como repetida).
        idempotency_key = IdempotencyService.compute_key(
            tipo or "desconocido", payload, correlation_id
        )
        logger.info(
            "Sin idempotencyKey/messageId en el sobre; se usa una clave "
            "derivada del contenido del comando."
        )

    session_idem = db_module.SessionLocal()
    try:
        idempotencia = IdempotencyService(session_idem)
        idempotencia.check_or_run(idempotency_key, tipo or "desconocido", _run)
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
        global _consumidor_pulsar_activo
        client = pulsar.Client(settings.PULSAR_SERVICE_URL)
        consumidor = client.subscribe(
            settings.TOPICO_COMANDOS,
            subscription_name=settings.PULSAR_SUSCRIPCION,
            consumer_type=pulsar.ConsumerType.Shared,
        )
        _consumidor_pulsar_activo = True
        try:
            while True:
                mensaje = consumidor.receive()
                try:
                    procesar_mensaje(mensaje.data())
                    consumidor.acknowledge(mensaje)
                    eventos_consumidos_total.labels(resultado="ok").inc()
                except Exception:
                    logger.exception("Fallo procesando un comando; se hace nack.")
                    consumidor.negative_acknowledge(mensaje)
                    eventos_consumidos_total.labels(resultado="fallido").inc()
        finally:
            # Si receive()/acknowledge() lanzan por una desconexion real del
            # broker, marcamos la replica como no lista antes de que el hilo
            # muera (mismo comportamiento de antes, solo se agrega la senal).
            _consumidor_pulsar_activo = False

    hilo = threading.Thread(target=_bucle, name="consumidor-pulsar", daemon=True)
    hilo.start()
    return hilo
