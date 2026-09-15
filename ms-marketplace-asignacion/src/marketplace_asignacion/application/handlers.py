from __future__ import annotations
import logging

from marketplace_asignacion.application.commands import (
    SolicitarTrabajo,
    PublicarTrabajo,
    SeleccionarProveedor,
)
from marketplace_asignacion.application.unit_of_work import UnitOfWork
from marketplace_asignacion.application.outbox_port import OutboxStore
from marketplace_asignacion.application.integration_events import (
    ProveedorSeleccionadoParaValidacion,
    GenerarCotizacionCommand,
    ProveedorAsignadoAlTrabajo,
    NotificarProveedorAsignadoCommand,
    NotificarClienteProveedorAsignadoCommand,
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

        # ── Integración: Cotizaciones ──────────────────────────────
        cotizacion_cmd = GenerarCotizacionCommand(
            correlation_id=cmd.correlation_id,
            aggregate_id=trabajo.id,
            trabajo_id=trabajo.id,
            cliente_id=trabajo.cliente_id,
            ubicacion={
                "direccion": trabajo.ubicacion.direccion,
                "ciudad": trabajo.ubicacion.ciudad,
                "pais": trabajo.ubicacion.pais,
                "codigo_postal": trabajo.ubicacion.codigo_postal,
            }
            if trabajo.ubicacion
            else None,
            alcance={
                "descripcion": trabajo.alcance.descripcion,
                "categoria": trabajo.alcance.categoria,
                "notas": trabajo.alcance.notas,
            }
            if trabajo.alcance
            else None,
        )
        self._outbox.store([cotizacion_cmd])

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
                    "GenerarCotizacionCommand",
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

        # ── Integración: Verificación y Acreditación ───────────────
        evento_validacion = ProveedorSeleccionadoParaValidacion(
            correlation_id=cmd.correlation_id,
            aggregate_id=cmd.proveedor_id,
            proveedor_id=cmd.proveedor_id,
            trabajo_id=cmd.trabajo_id,
        )
        self._outbox.store([evento_validacion])

        # ── Integración: Broadcast proveedor asignado ──────────────
        asignado = ProveedorAsignadoAlTrabajo(
            correlation_id=cmd.correlation_id,
            aggregate_id=cmd.trabajo_id,
            trabajo_id=cmd.trabajo_id,
            proveedor_id=cmd.proveedor_id,
            cliente_id=trabajo.cliente_id,
        )
        self._outbox.store([asignado])

        # ── Integración: Notificaciones ────────────────────────────
        notificar_proveedor = NotificarProveedorAsignadoCommand(
            correlation_id=cmd.correlation_id,
            aggregate_id=cmd.proveedor_id,
            proveedor_id=cmd.proveedor_id,
            trabajo_id=cmd.trabajo_id,
            cliente_id=trabajo.cliente_id,
            detalles_trabajo={
                "descripcion": trabajo.alcance.descripcion if trabajo.alcance else None,
                "categoria": trabajo.alcance.categoria if trabajo.alcance else None,
                "ubicacion": {
                    "direccion": trabajo.ubicacion.direccion,
                    "ciudad": trabajo.ubicacion.ciudad,
                }
                if trabajo.ubicacion
                else None,
            },
        )
        notificar_cliente = NotificarClienteProveedorAsignadoCommand(
            correlation_id=cmd.correlation_id,
            aggregate_id=trabajo.id,
            cliente_id=trabajo.cliente_id,
            trabajo_id=cmd.trabajo_id,
            proveedor_id=cmd.proveedor_id,
        )
        self._outbox.store([notificar_proveedor, notificar_cliente])

        logger.info(
            "Proveedor seleccionado",
            extra={
                "trabajo_id": str(trabajo.id),
                "proveedor_id": str(cmd.proveedor_id),
                "correlation_id": cmd.correlation_id,
                "eventos_integracion": [
                    "ProveedorSeleccionadoParaValidacion",
                    "ProveedorAsignadoAlTrabajo",
                    "NotificarProveedorAsignadoCommand",
                    "NotificarClienteProveedorAsignadoCommand",
                ],
            },
        )
        return trabajo
