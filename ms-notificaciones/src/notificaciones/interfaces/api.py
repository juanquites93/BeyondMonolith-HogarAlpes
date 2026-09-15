from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from notificaciones.infrastructure import database as db_module
from notificaciones.infrastructure.repositories import SqlAlchemyNotificacionRepository
from notificaciones.interfaces.schemas import NotificacionResponse

router = APIRouter()


def get_db():
    db = db_module.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _to_response(notificacion) -> NotificacionResponse:
    return NotificacionResponse(
        notificacion_id=notificacion.id,
        destinatario_id=notificacion.destinatario.id,
        tipo=notificacion.tipo,
        canal=notificacion.canal.value,
        trabajo_id=notificacion.trabajo_id,
        estado=notificacion.estado.value,
        motivo_fallo=notificacion.motivo_fallo,
    )


@router.get("/notificaciones/{notificacion_id}", response_model=NotificacionResponse)
def obtener_notificacion(
    notificacion_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    repo = SqlAlchemyNotificacionRepository(db)
    notificacion = repo.get(notificacion_id)
    if notificacion is None:
        raise HTTPException(status_code=404, detail="Notificacion no encontrada")
    return _to_response(notificacion)
