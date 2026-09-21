"""Router de la API REST."""

from __future__ import annotations
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from verificacion_acreditacion.application.commands import (
    IniciarVerificacionProveedor,
    AprobarVerificacionProveedor,
    RechazarVerificacionProveedor,
    AcreditarProveedor,
    RevocarAcreditacionProveedor,
)
from verificacion_acreditacion.application.handlers import CommandHandler
from verificacion_acreditacion.infrastructure import database as db_module
from verificacion_acreditacion.infrastructure.unit_of_work_impl import (
    SqlAlchemyUnitOfWork,
)
from verificacion_acreditacion.infrastructure.outbox import SqlAlchemyOutboxStore
from verificacion_acreditacion.infrastructure.idempotency import IdempotencyService
from verificacion_acreditacion.interfaces.api.schemas import (
    IniciarVerificacionRequest,
    AprobarVerificacionRequest,
    RechazarVerificacionRequest,
    AcreditarProveedorRequest,
    RevocarAcreditacionRequest,
    ProveedorResponse,
)
from verificacion_acreditacion.domain.exceptions import VerificacionError
from verificacion_acreditacion.infrastructure.fake_external_validation_adapter import (
    FakeExternalValidationAdapter,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def get_db():
    db = db_module.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _to_response(proveedor) -> ProveedorResponse:
    return ProveedorResponse(
        proveedor_id=proveedor.id,
        estado_verificacion=proveedor.estado_verificacion.value,
        estado_acreditacion=proveedor.estado_acreditacion.value,
    )


_external_validation = FakeExternalValidationAdapter()


@router.post(
    "/verificaciones",
    response_model=ProveedorResponse,
    status_code=status.HTTP_201_CREATED,
)
def iniciar_verificacion(
    request: IniciarVerificacionRequest, db: Session = Depends(get_db)
):
    key = request.idempotency_key or IdempotencyService.compute_key(
        "IniciarVerificacionProveedor",
        request.model_dump(mode="json", exclude={"idempotency_key"}),
        request.correlation_id,
    )
    idempotency = IdempotencyService(db)

    def _run():
        uow = SqlAlchemyUnitOfWork()
        outbox = SqlAlchemyOutboxStore()
        handler = CommandHandler(uow, outbox, _external_validation)
        cmd = IniciarVerificacionProveedor(
            proveedor_id=request.proveedor_id,
            correlation_id=request.correlation_id,
        )
        with uow:
            outbox.bind(uow.session)
            proveedor = handler.handle_iniciar_verificacion(cmd)
        proveedor.limpiar_eventos()
        return proveedor

    try:
        result = idempotency.check_or_run(key, "IniciarVerificacionProveedor", _run)
    except VerificacionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    if isinstance(result, dict):
        return JSONResponse(content=result, status_code=200)
    return _to_response(result)


@router.post(
    "/verificaciones/{verificacion_id}/aprobar", response_model=ProveedorResponse
)
def aprobar_verificacion(
    verificacion_id: uuid.UUID,
    request: AprobarVerificacionRequest,
    db: Session = Depends(get_db),
):
    key = request.idempotency_key or IdempotencyService.compute_key(
        "AprobarVerificacionProveedor",
        {"verificacion_id": str(verificacion_id)},
        request.correlation_id,
    )
    idempotency = IdempotencyService(db)

    def _run():
        # El verificacion_id es meramente identificador de la operación en la API;
        # la lógica de dominio opera por proveedor_id. Para simplificar,
        # buscamos el proveedor que tenga una verificación activa (simulado:
        # usamos verificacion_id como proveedor_id para el demo local).
        uow = SqlAlchemyUnitOfWork()
        outbox = SqlAlchemyOutboxStore()
        handler = CommandHandler(uow, outbox, _external_validation)
        cmd = AprobarVerificacionProveedor(
            proveedor_id=verificacion_id,
            correlation_id=request.correlation_id,
        )
        with uow:
            outbox.bind(uow.session)
            proveedor = handler.handle_aprobar_verificacion(cmd)
        proveedor.limpiar_eventos()
        return proveedor

    try:
        result = idempotency.check_or_run(key, "AprobarVerificacionProveedor", _run)
    except VerificacionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    if isinstance(result, dict):
        return JSONResponse(content=result, status_code=200)
    return _to_response(result)


@router.post(
    "/verificaciones/{verificacion_id}/rechazar", response_model=ProveedorResponse
)
def rechazar_verificacion(
    verificacion_id: uuid.UUID,
    request: RechazarVerificacionRequest,
    db: Session = Depends(get_db),
):
    key = request.idempotency_key or IdempotencyService.compute_key(
        "RechazarVerificacionProveedor",
        {"verificacion_id": str(verificacion_id), "motivo": request.motivo},
        request.correlation_id,
    )
    idempotency = IdempotencyService(db)

    def _run():
        uow = SqlAlchemyUnitOfWork()
        outbox = SqlAlchemyOutboxStore()
        handler = CommandHandler(uow, outbox, _external_validation)
        cmd = RechazarVerificacionProveedor(
            proveedor_id=verificacion_id,
            motivo=request.motivo,
            correlation_id=request.correlation_id,
        )
        with uow:
            outbox.bind(uow.session)
            proveedor = handler.handle_rechazar_verificacion(cmd)
        proveedor.limpiar_eventos()
        return proveedor

    try:
        result = idempotency.check_or_run(key, "RechazarVerificacionProveedor", _run)
    except VerificacionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    if isinstance(result, dict):
        return JSONResponse(content=result, status_code=200)
    return _to_response(result)


@router.post(
    "/acreditaciones",
    response_model=ProveedorResponse,
    status_code=status.HTTP_201_CREATED,
)
def acreditar_proveedor(
    request: AcreditarProveedorRequest, db: Session = Depends(get_db)
):
    key = request.idempotency_key or IdempotencyService.compute_key(
        "AcreditarProveedor",
        request.model_dump(mode="json", exclude={"idempotency_key"}),
        request.correlation_id,
    )
    idempotency = IdempotencyService(db)

    def _run():
        uow = SqlAlchemyUnitOfWork()
        outbox = SqlAlchemyOutboxStore()
        handler = CommandHandler(uow, outbox, _external_validation)
        cmd = AcreditarProveedor(
            proveedor_id=request.proveedor_id,
            correlation_id=request.correlation_id,
        )
        with uow:
            outbox.bind(uow.session)
            proveedor = handler.handle_acreditar_proveedor(cmd)
        proveedor.limpiar_eventos()
        return proveedor

    try:
        result = idempotency.check_or_run(key, "AcreditarProveedor", _run)
    except VerificacionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    if isinstance(result, dict):
        return JSONResponse(content=result, status_code=200)
    return _to_response(result)


@router.get("/proveedores/{proveedor_id}/estado", response_model=ProveedorResponse)
def obtener_estado_proveedor(proveedor_id: uuid.UUID, db: Session = Depends(get_db)):
    from verificacion_acreditacion.infrastructure.repositories import (
        SqlAlchemyProveedorRepository,
    )

    repo = SqlAlchemyProveedorRepository(db)
    proveedor = repo.get(proveedor_id)
    if proveedor is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return _to_response(proveedor)


@router.post(
    "/acreditaciones/{acreditacion_id}/revocar",
    response_model=ProveedorResponse,
)
def revocar_acreditacion(
    acreditacion_id: uuid.UUID,
    request: RevocarAcreditacionRequest,
    db: Session = Depends(get_db),
):
    key = request.idempotency_key or IdempotencyService.compute_key(
        "RevocarAcreditacionProveedor",
        {"acreditacion_id": str(acreditacion_id)},
        request.correlation_id,
    )
    idempotency = IdempotencyService(db)

    def _run():
        uow = SqlAlchemyUnitOfWork()
        outbox = SqlAlchemyOutboxStore()
        handler = CommandHandler(uow, outbox, _external_validation)
        # En el demo local usamos acreditacion_id como proveedor_id.
        cmd = RevocarAcreditacionProveedor(
            proveedor_id=acreditacion_id,
            acreditacion_id=request.acreditacion_id,
            correlation_id=request.correlation_id,
        )
        with uow:
            outbox.bind(uow.session)
            proveedor = handler.handle_revocar_acreditacion(cmd)
        proveedor.limpiar_eventos()
        return proveedor

    try:
        result = idempotency.check_or_run(key, "RevocarAcreditacionProveedor", _run)
    except VerificacionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    if isinstance(result, dict):
        return JSONResponse(content=result, status_code=200)
    return _to_response(result)


class DependenciaExternaEstadoRequest(BaseModel):
    disponible: bool


@router.post("/debug/dependencia-externa")
def controlar_dependencia_externa(request: DependenciaExternaEstadoRequest):
    """Endpoint de utilidad para demos.

    Permite marcar la dependencia externa de validación como disponible o caída,
    para probar el flujo de reintentos de la Saga orquestada.
    """
    if request.disponible:
        _external_validation.marcar_disponible()
    else:
        _external_validation.marcar_caida()

    return {
        "disponible": _external_validation.esta_disponible(),
        "detail": (
            "Dependencia externa marcada como disponible"
            if request.disponible
            else "Dependencia externa marcada como caída"
        ),
    }
