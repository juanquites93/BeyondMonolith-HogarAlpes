from __future__ import annotations
import uuid
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status

from generador_cotizacion.application.commands import (
    SolicitarCotizacion,
    ActualizarCotizacion,
    EliminarCotizacion,
)
from generador_cotizacion.application.handlers import CommandHandler
from generador_cotizacion.infrastructure.unit_of_work_impl import SqlAlchemyUnitOfWork
from generador_cotizacion.infrastructure.outbox import SqlAlchemyOutboxStore
from generador_cotizacion.interfaces.schemas import (
    SolicitarCotizacionRequest,
    ActualizarCotizacionRequest,
    CotizacionResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_response(cotizacion) -> CotizacionResponse:
    return CotizacionResponse(
        cotizacion_id=cotizacion.id,
        trabajo_id=cotizacion.trabajo_id,
        proveedor_id=cotizacion.proveedor_id,
        monto=cotizacion.monto,
        moneda=cotizacion.moneda,
        descripcion=cotizacion.descripcion,
        estado=cotizacion.estado.value,
        fecha_solicitud=cotizacion.fecha_solicitud,
        fecha_validez=cotizacion.fecha_validez,
    )


@router.post(
    "/cotizaciones/solicitar",
    response_model=CotizacionResponse,
    status_code=status.HTTP_201_CREATED,
)
def solicitar_cotizacion(request: SolicitarCotizacionRequest):
    uow = SqlAlchemyUnitOfWork()
    outbox = SqlAlchemyOutboxStore()
    handler = CommandHandler(uow, outbox)
    cmd = SolicitarCotizacion(
        trabajo_id=request.trabajo_id,
        proveedor_id=request.proveedor_id,
        monto=request.monto,
        descripcion=request.descripcion,
        moneda=request.moneda,
        fecha_validez=request.fecha_validez,
        correlation_id=request.correlation_id,
    )
    with uow:
        outbox.bind(uow.session)
        cotizacion = handler.handle_solicitar_cotizacion(cmd)
    cotizacion.limpiar_eventos()

    # El relay del outbox hacia Pulsar corre en un background thread (ver main.py)
    return _to_response(cotizacion)


@router.get("/cotizaciones/{cotizacion_id}", response_model=CotizacionResponse)
def obtener_cotizacion(cotizacion_id: uuid.UUID):
    uow = SqlAlchemyUnitOfWork()
    outbox = SqlAlchemyOutboxStore()
    handler = CommandHandler(uow, outbox)
    with uow:
        cotizacion = handler.handle_obtener_cotizacion(cotizacion_id)
        if cotizacion is None:
            raise HTTPException(status_code=404, detail="Cotización no encontrada")
        return _to_response(cotizacion)


@router.get("/cotizaciones", response_model=List[CotizacionResponse])
def listar_cotizaciones(trabajo_id: Optional[uuid.UUID] = None):
    uow = SqlAlchemyUnitOfWork()
    outbox = SqlAlchemyOutboxStore()
    handler = CommandHandler(uow, outbox)
    with uow:
        cotizaciones = handler.handle_listar_cotizaciones(trabajo_id)
        return [_to_response(c) for c in cotizaciones]


@router.put("/cotizaciones/{cotizacion_id}", response_model=CotizacionResponse)
def actualizar_cotizacion(
    cotizacion_id: uuid.UUID, request: ActualizarCotizacionRequest
):
    uow = SqlAlchemyUnitOfWork()
    outbox = SqlAlchemyOutboxStore()
    handler = CommandHandler(uow, outbox)
    cmd = ActualizarCotizacion(
        cotizacion_id=cotizacion_id,
        proveedor_id=request.proveedor_id,
        monto=request.monto,
        descripcion=request.descripcion,
        estado=request.estado,
        fecha_validez=request.fecha_validez,
    )
    try:
        with uow:
            cotizacion = handler.handle_actualizar_cotizacion(cmd)
            response = _to_response(cotizacion)
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/cotizaciones/{cotizacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cotizacion(cotizacion_id: uuid.UUID):
    uow = SqlAlchemyUnitOfWork()
    outbox = SqlAlchemyOutboxStore()
    handler = CommandHandler(uow, outbox)
    cmd = EliminarCotizacion(cotizacion_id=cotizacion_id)
    try:
        with uow:
            handler.handle_eliminar_cotizacion(cmd)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
