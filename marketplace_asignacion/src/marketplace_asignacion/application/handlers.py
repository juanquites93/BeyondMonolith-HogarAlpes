from __future__ import annotations
import logging

from marketplace_asignacion.application.commands import (
    SolicitarTrabajo,
    PublicarTrabajo,
    SeleccionarProveedor,
)
from marketplace_asignacion.application.unit_of_work import UnitOfWork
from marketplace_asignacion.application.outbox_port import OutboxStore
from marketplace_asignacion.domain.model import Trabajo
from marketplace_asignacion.domain.value_objects import Ubicacion, Alcance
from marketplace_asignacion.domain.services import AsignacionService, AcreditacionPort

logger = logging.getLogger(__name__)


class CommandHandler:
    def __init__(
        self,
        uow: UnitOfWork,
        outbox: OutboxStore,
        acreditacion: AcreditacionPort,
    ):
        self._uow = uow
        self._outbox = outbox
        self._acreditacion = acreditacion

    def handle_solicitar_trabajo(self, cmd: SolicitarTrabajo) -> Trabajo:
        ubicacion = Ubicacion(
            direccion=cmd.direccion,
            ciudad=cmd.ciudad,
            pais=cmd.pais,
            codigo_postal=cmd.codigo_postal,
        )
        alcance = Alcance(
            descripcion=cmd.descripcion,
            categoria=cmd.categoria,
            notas=cmd.notas,
        )
        trabajo = Trabajo(
            cliente_id=cmd.cliente_id,
            ubicacion=ubicacion,
            alcance=alcance,
        )
        trabajo.solicitar(correlation_id=cmd.correlation_id)
        self._uow.trabajos.add(trabajo)
        self._outbox.store(trabajo.eventos)
        logger.info("Trabajo solicitado", extra={"trabajo_id": str(trabajo.id)})
        return trabajo

    def handle_publicar_trabajo(self, cmd: PublicarTrabajo) -> Trabajo:
        trabajo = self._uow.trabajos.get(cmd.trabajo_id)
        if trabajo is None:
            raise ValueError(f"Trabajo {cmd.trabajo_id} no encontrado")
        trabajo.publicar(correlation_id=cmd.correlation_id)
        self._uow.trabajos.update(trabajo)
        self._outbox.store(trabajo.eventos)
        logger.info("Trabajo publicado", extra={"trabajo_id": str(trabajo.id)})
        return trabajo

    def handle_seleccionar_proveedor(self, cmd: SeleccionarProveedor) -> Trabajo:
        servicio = AsignacionService(
            trabajo_repo=self._uow.trabajos,
            acreditacion=self._acreditacion,
        )
        trabajo = servicio.seleccionar_proveedor_para_trabajo(
            trabajo_id=cmd.trabajo_id,
            proveedor_id=cmd.proveedor_id,
            correlation_id=cmd.correlation_id,
        )
        self._outbox.store(trabajo.eventos)
        logger.info(
            "Proveedor seleccionado",
            extra={
                "trabajo_id": str(trabajo.id),
                "proveedor_id": str(cmd.proveedor_id),
            },
        )
        return trabajo
