from __future__ import annotations
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from marketplace_asignacion.application.commands import (
    SolicitarTrabajo,
    PublicarTrabajo,
    SeleccionarProveedor,
)
from marketplace_asignacion.application.handlers import CommandHandler
from marketplace_asignacion.infrastructure import database as db_module
from marketplace_asignacion.infrastructure.unit_of_work_impl import SqlAlchemyUnitOfWork
from marketplace_asignacion.infrastructure.outbox import SqlAlchemyOutboxStore
from marketplace_asignacion.infrastructure.acreditacion_adapter import (
    FakeAcreditacionAdapter,
)
from marketplace_asignacion.infrastructure.event_publisher import (
    SimulatedEventPublisher,
)
from marketplace_asignacion.infrastructure.idempotency import IdempotencyService
from marketplace_asignacion.interfaces.schemas import (
    SolicitarTrabajoRequest,
    PublicarTrabajoRequest,
    SeleccionarProveedorRequest,
    TrabajoResponse,
    UbicacionSchema,
    AlcanceSchema,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Estado compartido en memoria para demo (lista de proveedores acreditados)
_acreditacion_adapter = FakeAcreditacionAdapter()


def get_db():
    db = db_module.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_acreditacion_adapter():
    return _acreditacion_adapter


def _to_response(trabajo) -> TrabajoResponse:
    return TrabajoResponse(
        trabajo_id=trabajo.id,
        cliente_id=trabajo.cliente_id,
        estado=trabajo.estado.value,
        proveedor_seleccionado_id=trabajo.proveedor_seleccionado_id,
        ubicacion=UbicacionSchema(
            direccion=trabajo.ubicacion.direccion,
            ciudad=trabajo.ubicacion.ciudad,
            pais=trabajo.ubicacion.pais,
            codigo_postal=trabajo.ubicacion.codigo_postal,
        )
        if trabajo.ubicacion
        else None,
        alcance=AlcanceSchema(
            descripcion=trabajo.alcance.descripcion,
            categoria=trabajo.alcance.categoria,
            notas=trabajo.alcance.notas,
        )
        if trabajo.alcance
        else None,
    )


@router.post(
    "/trabajos/solicitar",
    response_model=TrabajoResponse,
    status_code=status.HTTP_201_CREATED,
)
def solicitar_trabajo(
    request: SolicitarTrabajoRequest,
    db: Session = Depends(get_db),
):
    key = request.idempotency_key or IdempotencyService.compute_key(
        "SolicitarTrabajo",
        request.model_dump(mode="json", exclude={"idempotency_key"}),
        request.correlation_id,
    )
    idempotency = IdempotencyService(db)

    def _run():
        uow = SqlAlchemyUnitOfWork()
        outbox = SqlAlchemyOutboxStore()
        handler = CommandHandler(uow, outbox, get_acreditacion_adapter())
        cmd = SolicitarTrabajo(
            cliente_id=request.cliente_id,
            direccion=request.ubicacion.direccion,
            ciudad=request.ubicacion.ciudad,
            pais=request.ubicacion.pais,
            codigo_postal=request.ubicacion.codigo_postal,
            descripcion=request.alcance.descripcion,
            categoria=request.alcance.categoria,
            notas=request.alcance.notas,
            correlation_id=request.correlation_id,
        )
        with uow:
            outbox.bind(uow.session)
            trabajo = handler.handle_solicitar_trabajo(cmd)
        trabajo.limpiar_eventos()
        return trabajo

    result = idempotency.check_or_run(key, "SolicitarTrabajo", _run)
    if isinstance(result, dict):
        return JSONResponse(content=result, status_code=200)

    # Publicar eventos pendientes (simula relay del outbox al broker)
    SimulatedEventPublisher(db_module.SessionLocal).publish_pending()
    return _to_response(result)


@router.post("/trabajos/{trabajo_id}/publicar", response_model=TrabajoResponse)
def publicar_trabajo(
    trabajo_id: uuid.UUID,
    request: PublicarTrabajoRequest,
    db: Session = Depends(get_db),
):
    key = request.idempotency_key or IdempotencyService.compute_key(
        "PublicarTrabajo",
        {"trabajo_id": str(trabajo_id)},
        request.correlation_id,
    )
    idempotency = IdempotencyService(db)

    def _run():
        uow = SqlAlchemyUnitOfWork()
        outbox = SqlAlchemyOutboxStore()
        handler = CommandHandler(uow, outbox, get_acreditacion_adapter())
        cmd = PublicarTrabajo(
            trabajo_id=trabajo_id,
            correlation_id=request.correlation_id,
        )
        with uow:
            outbox.bind(uow.session)
            trabajo = handler.handle_publicar_trabajo(cmd)
        trabajo.limpiar_eventos()
        return trabajo

    result = idempotency.check_or_run(key, "PublicarTrabajo", _run)
    if isinstance(result, dict):
        return JSONResponse(content=result, status_code=200)

    SimulatedEventPublisher(db_module.SessionLocal).publish_pending()
    return _to_response(result)


@router.post(
    "/trabajos/{trabajo_id}/seleccionar-proveedor", response_model=TrabajoResponse
)
def seleccionar_proveedor(
    trabajo_id: uuid.UUID,
    request: SeleccionarProveedorRequest,
    db: Session = Depends(get_db),
):
    key = request.idempotency_key or IdempotencyService.compute_key(
        "SeleccionarProveedor",
        {"trabajo_id": str(trabajo_id), "proveedor_id": str(request.proveedor_id)},
        request.correlation_id,
    )
    idempotency = IdempotencyService(db)

    def _run():
        uow = SqlAlchemyUnitOfWork()
        outbox = SqlAlchemyOutboxStore()
        handler = CommandHandler(uow, outbox, get_acreditacion_adapter())
        cmd = SeleccionarProveedor(
            trabajo_id=trabajo_id,
            proveedor_id=request.proveedor_id,
            correlation_id=request.correlation_id,
        )
        with uow:
            outbox.bind(uow.session)
            trabajo = handler.handle_seleccionar_proveedor(cmd)
        trabajo.limpiar_eventos()
        return trabajo

    result = idempotency.check_or_run(key, "SeleccionarProveedor", _run)
    if isinstance(result, dict):
        return JSONResponse(content=result, status_code=200)

    SimulatedEventPublisher(db_module.SessionLocal).publish_pending()
    return _to_response(result)


@router.get("/trabajos/{trabajo_id}", response_model=TrabajoResponse)
def obtener_trabajo(
    trabajo_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    from marketplace_asignacion.infrastructure.repositories import (
        SqlAlchemyTrabajoRepository,
    )

    repo = SqlAlchemyTrabajoRepository(db)
    trabajo = repo.get(trabajo_id)
    if trabajo is None:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    return _to_response(trabajo)
