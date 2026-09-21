from __future__ import annotations
import logging

from marketplace_asignacion.application.commands import (
    SolicitarTrabajo,
    PublicarTrabajo,
    SeleccionarProveedor,
    RevertirSeleccionProveedor,
)
from marketplace_asignacion.application.unit_of_work import UnitOfWork
from marketplace_asignacion.application.outbox_port import OutboxStore
from marketplace_asignacion.application.integration_events import (
    ProveedorAsignadoAlTrabajo,
    TrabajoActualizado,
)
from marketplace_asignacion.domain.model import Trabajo
from marketplace_asignacion.domain.value_objects import (
    Ubicacion,
    Alcance,
    EstadoTrabajo,
)
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
        logger.info(
            "Trabajo solicitado",
            extra={"trabajo_id": str(trabajo.id), "correlation_id": cmd.correlation_id},
        )
        return trabajo

    def handle_publicar_trabajo(self, cmd: PublicarTrabajo) -> Trabajo:
        trabajo = self._uow.trabajos.get(cmd.trabajo_id)
        if trabajo is None:
            raise ValueError(f"Trabajo {cmd.trabajo_id} no encontrado")

        estado_anterior = trabajo.estado.value
        trabajo.publicar(correlation_id=cmd.correlation_id)
        self._uow.trabajos.update(trabajo)
        self._outbox.store(trabajo.eventos)

        # ── Integración: Broadcast estado actualizado ───────────────
        actualizado = TrabajoActualizado(
            correlation_id=cmd.correlation_id,
            aggregate_id=trabajo.id,
            trabajo_id=trabajo.id,
            cliente_id=trabajo.cliente_id,
            estado_anterior=estado_anterior,
            estado_nuevo=trabajo.estado.value,
        )
        self._outbox.store([actualizado])

        logger.info(
            "Trabajo publicado",
            extra={
                "trabajo_id": str(trabajo.id),
                "correlation_id": cmd.correlation_id,
                "eventos_integracion": [
                    "TrabajoActualizado",
                ],
            },
        )
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

        # ── Integración: Broadcast proveedor asignado ──────────────
        # La coordinación con verificación, cotización y notificaciones ahora
        # la realiza el orquestador centralizado (ms-orquestador) mediante Saga.
        asignado = ProveedorAsignadoAlTrabajo(
            correlation_id=cmd.correlation_id,
            aggregate_id=cmd.trabajo_id,
            trabajo_id=cmd.trabajo_id,
            proveedor_id=cmd.proveedor_id,
            cliente_id=trabajo.cliente_id,
        )
        self._outbox.store([asignado])

        logger.info(
            "Proveedor seleccionado",
            extra={
                "trabajo_id": str(trabajo.id),
                "proveedor_id": str(cmd.proveedor_id),
                "correlation_id": cmd.correlation_id,
                "eventos_integracion": [
                    "ProveedorAsignadoAlTrabajo",
                ],
            },
        )
        return trabajo

    def handle_revertir_seleccion_proveedor(
        self, cmd: RevertirSeleccionProveedor
    ) -> Trabajo:
        servicio = AsignacionService(
            trabajo_repo=self._uow.trabajos,
            acreditacion=self._acreditacion,
        )
        trabajo = servicio.revertir_seleccion_proveedor(
            trabajo_id=cmd.trabajo_id,
            correlation_id=cmd.correlation_id,
        )
        self._outbox.store(trabajo.eventos)
        logger.info(
            "Selección de proveedor revertida",
            extra={
                "trabajo_id": str(trabajo.id),
                "correlation_id": cmd.correlation_id,
            },
        )
        return trabajo
