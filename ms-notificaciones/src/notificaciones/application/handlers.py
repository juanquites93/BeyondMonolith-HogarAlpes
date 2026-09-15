from __future__ import annotations
import logging

from notificaciones.application.commands import (
    NotificarProveedorAsignado,
    NotificarClienteProveedorAsignado,
)
from notificaciones.application.unit_of_work import UnitOfWork
from notificaciones.application.outbox_port import OutboxStore
from notificaciones.domain.model import Notificacion
from notificaciones.domain.services import PasarelaPort
from notificaciones.domain.value_objects import Canal, Destinatario

logger = logging.getLogger(__name__)

# El contacto real de cliente_id/proveedor_id no llega en el comando (solo el
# id): mientras el equipo defina como resolverlo, se usa un contacto de
# ejemplo derivado del id.
_DOMINIO_CONTACTO_DEMO = "hogaralpes.demo"


def _contacto_demo(identificador: str) -> str:
    return f"{identificador}@{_DOMINIO_CONTACTO_DEMO}"


class CommandHandler:
    def __init__(
        self,
        uow: UnitOfWork,
        outbox: OutboxStore,
        pasarela: PasarelaPort,
    ):
        self._uow = uow
        self._outbox = outbox
        self._pasarela = pasarela

    def _enviar(self, notificacion: Notificacion, correlation_id) -> Notificacion:
        contacto = notificacion.destinatario.contacto
        exitoso = self._pasarela.enviar(
            notificacion.canal, contacto, notificacion.asunto, notificacion.cuerpo
        )
        if exitoso:
            notificacion.marcar_enviada(correlation_id=correlation_id)
        else:
            notificacion.marcar_fallida("la pasarela no acepto el envio", correlation_id=correlation_id)
        return notificacion

    def handle_notificar_proveedor_asignado(
        self, cmd: NotificarProveedorAsignado
    ) -> Notificacion:
        destinatario = Destinatario(
            id=cmd.proveedor_id,
            nombre=f"Proveedor {cmd.proveedor_id}",
            contacto=_contacto_demo(cmd.proveedor_id),
        )
        notificacion = Notificacion(
            destinatario=destinatario,
            tipo="TRABAJO_ASIGNADO",
            canal=Canal.EMAIL,
            trabajo_id=cmd.trabajo_id,
            asunto="Tienes un trabajo nuevo",
            cuerpo=(
                f"Hola {destinatario.nombre}, tienes un nuevo trabajo de "
                f"{cmd.categoria} en {cmd.ciudad}: {cmd.descripcion}."
            ),
        )
        notificacion.solicitar(correlation_id=cmd.correlation_id)
        self._uow.notificaciones.add(notificacion)
        self._enviar(notificacion, cmd.correlation_id)
        self._uow.notificaciones.update(notificacion)
        self._outbox.store(notificacion.eventos)
        logger.info(
            "Notificacion de trabajo asignado procesada",
            extra={"notificacion_id": str(notificacion.id)},
        )
        return notificacion

    def handle_notificar_cliente_proveedor_asignado(
        self, cmd: NotificarClienteProveedorAsignado
    ) -> Notificacion:
        destinatario = Destinatario(
            id=cmd.cliente_id,
            nombre=f"Cliente {cmd.cliente_id}",
            contacto=_contacto_demo(cmd.cliente_id),
        )
        notificacion = Notificacion(
            destinatario=destinatario,
            tipo="PROVEEDOR_ASIGNADO",
            canal=Canal.EMAIL,
            trabajo_id=cmd.trabajo_id,
            asunto="Ya tienes un proveedor asignado",
            cuerpo=(
                f"Hola {destinatario.nombre}, el proveedor {cmd.proveedor_id} "
                f"fue asignado a tu solicitud y te contactara pronto."
            ),
        )
        notificacion.solicitar(correlation_id=cmd.correlation_id)
        self._uow.notificaciones.add(notificacion)
        self._enviar(notificacion, cmd.correlation_id)
        self._uow.notificaciones.update(notificacion)
        self._outbox.store(notificacion.eventos)
        logger.info(
            "Notificacion de proveedor asignado procesada",
            extra={"notificacion_id": str(notificacion.id)},
        )
        return notificacion
