"""API REST del orquestador para consultar Sagas."""

from __future__ import annotations
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ms_orquestador.infrastructure import database as db_module
from ms_orquestador.infrastructure.saga_repository import SagaRepository

logger = logging.getLogger(__name__)
router = APIRouter()


def get_db():
    db = db_module.SessionLocal()
    try:
        yield db
    finally:
        db.close()


class SagaLogResponse(BaseModel):
    id: str
    saga_id: str
    correlation_id: Optional[str]
    message_id: Optional[str]
    causation_id: Optional[str]
    message_type: str
    producer: str
    status: str
    payload: dict
    error_message: Optional[str]
    occurred_at: Optional[str]

    class Config:
        from_attributes = True


class SagaResponse(BaseModel):
    saga_id: str
    correlation_id: Optional[str]
    trabajo_id: Optional[str]
    proveedor_id: Optional[str]
    current_state: str
    retry_count: int
    last_event_type: Optional[str]
    last_error: Optional[str]
    compensated_steps: Optional[list]
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


@router.get("/sagas", response_model=List[SagaResponse])
def listar_sagas(
    estado: Optional[str] = None,
    trabajo_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(db_module.Base.metadata.tables["sagas"])
    if estado:
        query = query.filter(
            db_module.Base.metadata.tables["sagas"].c.current_state == estado
        )
    if trabajo_id:
        query = query.filter(
            db_module.Base.metadata.tables["sagas"].c.trabajo_id == trabajo_id
        )
    rows = query.order_by(
        db_module.Base.metadata.tables["sagas"].c.created_at.desc()
    ).all()
    return [
        {
            **dict(row._mapping),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    ]


@router.get("/sagas/{saga_id}", response_model=SagaResponse)
def obtener_saga(saga_id: str, db: Session = Depends(get_db)):
    repo = SagaRepository(db)
    saga = repo.get(saga_id)
    if saga is None:
        raise HTTPException(status_code=404, detail="Saga no encontrada")
    return {
        "saga_id": saga.saga_id,
        "correlation_id": saga.correlation_id,
        "trabajo_id": saga.trabajo_id,
        "proveedor_id": saga.proveedor_id,
        "current_state": saga.current_state,
        "retry_count": saga.retry_count,
        "last_event_type": saga.last_event_type,
        "last_error": saga.last_error,
        "compensated_steps": saga.compensated_steps,
        "created_at": saga.created_at.isoformat() if saga.created_at else None,
        "updated_at": saga.updated_at.isoformat() if saga.updated_at else None,
    }


@router.get("/sagas/{saga_id}/logs", response_model=List[SagaLogResponse])
def logs_de_saga(saga_id: str, db: Session = Depends(get_db)):
    repo = SagaRepository(db)
    # Acceso directo a la tabla para evitar exponer el ORM
    rows = (
        db.query(db_module.Base.metadata.tables["saga_logs"])
        .filter(db_module.Base.metadata.tables["saga_logs"].c.saga_id == saga_id)
        .order_by(db_module.Base.metadata.tables["saga_logs"].c.occurred_at.desc())
        .all()
    )
    return [
        {
            **dict(row._mapping),
            "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
        }
        for row in rows
    ]


@router.get("/sagas/{saga_id}/estado")
def estado_saga(saga_id: str, db: Session = Depends(get_db)):
    repo = SagaRepository(db)
    saga = repo.get(saga_id)
    if saga is None:
        raise HTTPException(status_code=404, detail="Saga no encontrada")
    return {"saga_id": saga_id, "estado": saga.current_state}
