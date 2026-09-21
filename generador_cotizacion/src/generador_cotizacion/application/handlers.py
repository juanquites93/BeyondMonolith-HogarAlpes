from __future__ import annotations
import logging
from typing import List, Optional

from generador_cotizacion.application.commands import (
    SolicitarCotizacion,
    GenerarCotizacion,
    ActualizarCotizacion,
    EliminarCotizacion,
    CancelarCotizacion,
)
from generador_cotizacion.application.unit_of_work import UnitOfWork
from generador_cotizacion.application.outbox_port import OutboxStore
from generador_cotizacion.domain.model import Cotizacion
from generador_cotizacion.domain.value_objects import EstadoCotizacion

logger = logging.getLogger(__name__)


class CommandHandler:
    def __init__(self, uow: UnitOfWork, outbox: OutboxStore):
        self._uow = uow
        self._outbox = outbox

    def handle_solicitar_cotizacion(self, cmd: SolicitarCotizacion) -> Cotizacion:
        cotizacion = Cotizacion.solicitar(
            trabajo_id=cmd.trabajo_id,
            proveedor_id=cmd.proveedor_id,
            monto=cmd.monto,
            descripcion=cmd.descripcion,
            moneda=cmd.moneda,
            fecha_validez=cmd.fecha_validez,
            correlation_id=cmd.correlation_id,
        )
        self._uow.cotizaciones.add(cotizacion)
        self._outbox.store(cotizacion.eventos)
        logger.info(
            "Cotización solicitada", extra={"cotizacion_id": str(cotizacion.id)}
        )
        return cotizacion

    def handle_generar_cotizacion(self, cmd: GenerarCotizacion) -> Cotizacion:
        cotizacion = Cotizacion.solicitar(
            trabajo_id=cmd.trabajo_id,
            descripcion=cmd.descripcion,
            correlation_id=cmd.correlation_id,
        )
        self._uow.cotizaciones.add(cotizacion)
        self._outbox.store(cotizacion.eventos)
        logger.info(
            "Cotización generada a partir de comando de integración",
            extra={
                "cotizacion_id": str(cotizacion.id),
                "trabajo_id": str(cmd.trabajo_id),
            },
        )
        return cotizacion

    def handle_actualizar_cotizacion(self, cmd: ActualizarCotizacion) -> Cotizacion:
        cotizacion = self._uow.cotizaciones.get(cmd.cotizacion_id)
        if cotizacion is None:
            raise ValueError(f"Cotización {cmd.cotizacion_id} no encontrada")
        if cmd.proveedor_id is not None:
            cotizacion.proveedor_id = cmd.proveedor_id
        if cmd.monto is not None:
            cotizacion.monto = cmd.monto
        if cmd.descripcion is not None:
            cotizacion.descripcion = cmd.descripcion
        if cmd.estado is not None:
            cotizacion.estado = EstadoCotizacion(cmd.estado)
        if cmd.fecha_validez is not None:
            cotizacion.fecha_validez = cmd.fecha_validez
        self._uow.cotizaciones.update(cotizacion)
        logger.info(
            "Cotización actualizada", extra={"cotizacion_id": str(cotizacion.id)}
        )
        return cotizacion

    def handle_eliminar_cotizacion(self, cmd: EliminarCotizacion) -> None:
        self._uow.cotizaciones.delete(cmd.cotizacion_id)
        logger.info(
            "Cotización eliminada", extra={"cotizacion_id": str(cmd.cotizacion_id)}
        )

    def handle_cancelar_cotizacion(self, cmd: CancelarCotizacion) -> Cotizacion:
        cotizacion = self._uow.cotizaciones.get(cmd.cotizacion_id)
        if cotizacion is None:
            raise ValueError(f"Cotización {cmd.cotizacion_id} no encontrada")
        cotizacion.cancelar(correlation_id=cmd.correlation_id)
        self._uow.cotizaciones.update(cotizacion)
        self._outbox.store(cotizacion.eventos)
        logger.info(
            "Cotización cancelada",
            extra={"cotizacion_id": str(cotizacion.id)},
        )
        return cotizacion

    def handle_obtener_cotizacion(self, cotizacion_id) -> Optional[Cotizacion]:
        return self._uow.cotizaciones.get(cotizacion_id)

    def handle_listar_cotizaciones(self, trabajo_id=None) -> List[Cotizacion]:
        return self._uow.cotizaciones.list(trabajo_id)
