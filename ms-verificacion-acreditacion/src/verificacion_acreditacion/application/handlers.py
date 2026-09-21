"""Handlers de comandos."""

from __future__ import annotations
import logging

from verificacion_acreditacion.application.commands import (
    IniciarVerificacionProveedor,
    AprobarVerificacionProveedor,
    RechazarVerificacionProveedor,
    AcreditarProveedor,
    RevocarAcreditacionProveedor,
)
from verificacion_acreditacion.application.unit_of_work import UnitOfWork
from verificacion_acreditacion.application.outbox_port import OutboxStore
from verificacion_acreditacion.application.external_validation_port import (
    ExternalValidationPort,
)
from verificacion_acreditacion.domain.services import VerificacionService
from verificacion_acreditacion.infrastructure.fake_external_validation_adapter import (
    FakeExternalValidationAdapter,
)

logger = logging.getLogger(__name__)


class CommandHandler:
    def __init__(
        self,
        uow: UnitOfWork,
        outbox: OutboxStore,
        external_validation: ExternalValidationPort = None,
    ):
        self._uow = uow
        self._outbox = outbox
        self._external_validation = (
            external_validation or FakeExternalValidationAdapter()
        )

    def handle_iniciar_verificacion(self, cmd: IniciarVerificacionProveedor):
        servicio = VerificacionService(self._uow.proveedores, self._external_validation)
        proveedor = servicio.iniciar_verificacion(
            proveedor_id=cmd.proveedor_id,
            trabajo_id=cmd.trabajo_id,
            correlation_id=cmd.correlation_id,
        )
        self._outbox.store(proveedor.eventos)
        eventos = [e.event_type for e in proveedor.eventos]
        logger.info(
            "Verificación procesada",
            extra={"proveedor_id": str(proveedor.id), "eventos": eventos},
        )
        return proveedor

    def handle_aprobar_verificacion(self, cmd: AprobarVerificacionProveedor):
        servicio = VerificacionService(self._uow.proveedores, self._external_validation)
        proveedor = servicio.aprobar_verificacion(
            proveedor_id=cmd.proveedor_id,
            correlation_id=cmd.correlation_id,
        )
        self._outbox.store(proveedor.eventos)
        logger.info("Verificación aprobada", extra={"proveedor_id": str(proveedor.id)})
        return proveedor

    def handle_rechazar_verificacion(self, cmd: RechazarVerificacionProveedor):
        servicio = VerificacionService(self._uow.proveedores, self._external_validation)
        proveedor = servicio.rechazar_verificacion(
            proveedor_id=cmd.proveedor_id,
            motivo=cmd.motivo,
            correlation_id=cmd.correlation_id,
        )
        self._outbox.store(proveedor.eventos)
        logger.info("Verificación rechazada", extra={"proveedor_id": str(proveedor.id)})
        return proveedor

    def handle_acreditar_proveedor(self, cmd: AcreditarProveedor):
        servicio = VerificacionService(self._uow.proveedores, self._external_validation)
        proveedor = servicio.acreditar_proveedor(
            proveedor_id=cmd.proveedor_id,
            correlation_id=cmd.correlation_id,
        )
        self._outbox.store(proveedor.eventos)
        logger.info("Proveedor acreditado", extra={"proveedor_id": str(proveedor.id)})
        return proveedor

    def handle_revocar_acreditacion(self, cmd: RevocarAcreditacionProveedor):
        servicio = VerificacionService(self._uow.proveedores, self._external_validation)
        proveedor = servicio.revocar_acreditacion(
            proveedor_id=cmd.proveedor_id,
            acreditacion_id=cmd.acreditacion_id,
            correlation_id=cmd.correlation_id,
        )
        self._outbox.store(proveedor.eventos)
        logger.info("Acreditación revocada", extra={"proveedor_id": str(proveedor.id)})
        return proveedor
