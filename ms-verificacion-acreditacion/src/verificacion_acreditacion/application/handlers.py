"""Handlers de comandos."""

from __future__ import annotations
import logging

from verificacion_acreditacion.application.commands import (
    IniciarVerificacionProveedor,
    AprobarVerificacionProveedor,
    RechazarVerificacionProveedor,
    AcreditarProveedor,
)
from verificacion_acreditacion.application.unit_of_work import UnitOfWork
from verificacion_acreditacion.application.outbox_port import OutboxStore
from verificacion_acreditacion.domain.services import VerificacionService

logger = logging.getLogger(__name__)


class CommandHandler:
    def __init__(self, uow: UnitOfWork, outbox: OutboxStore):
        self._uow = uow
        self._outbox = outbox

    def handle_iniciar_verificacion(self, cmd: IniciarVerificacionProveedor):
        servicio = VerificacionService(self._uow.proveedores)
        proveedor = servicio.iniciar_verificacion(
            proveedor_id=cmd.proveedor_id,
            correlation_id=cmd.correlation_id,
        )
        self._outbox.store(proveedor.eventos)
        logger.info("Verificación iniciada", extra={"proveedor_id": str(proveedor.id)})
        return proveedor

    def handle_aprobar_verificacion(self, cmd: AprobarVerificacionProveedor):
        servicio = VerificacionService(self._uow.proveedores)
        proveedor = servicio.aprobar_verificacion(
            proveedor_id=cmd.proveedor_id,
            correlation_id=cmd.correlation_id,
        )
        self._outbox.store(proveedor.eventos)
        logger.info("Verificación aprobada", extra={"proveedor_id": str(proveedor.id)})
        return proveedor

    def handle_rechazar_verificacion(self, cmd: RechazarVerificacionProveedor):
        servicio = VerificacionService(self._uow.proveedores)
        proveedor = servicio.rechazar_verificacion(
            proveedor_id=cmd.proveedor_id,
            motivo=cmd.motivo,
            correlation_id=cmd.correlation_id,
        )
        self._outbox.store(proveedor.eventos)
        logger.info("Verificación rechazada", extra={"proveedor_id": str(proveedor.id)})
        return proveedor

    def handle_acreditar_proveedor(self, cmd: AcreditarProveedor):
        servicio = VerificacionService(self._uow.proveedores)
        proveedor = servicio.acreditar_proveedor(
            proveedor_id=cmd.proveedor_id,
            correlation_id=cmd.correlation_id,
        )
        self._outbox.store(proveedor.eventos)
        logger.info("Proveedor acreditado", extra={"proveedor_id": str(proveedor.id)})
        return proveedor
