from __future__ import annotations
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from notificaciones.domain.model import Notificacion
from notificaciones.domain.repository import NotificacionRepository
from notificaciones.domain.value_objects import Canal, Destinatario, EstadoNotificacion
from notificaciones.infrastructure.orm import NotificacionORM


class SqlAlchemyNotificacionRepository(NotificacionRepository):
    def __init__(self, session: Session):
        self._session = session

    def get(self, id: uuid.UUID) -> Optional[Notificacion]:
        orm = self._session.get(NotificacionORM, str(id))
        if orm is None:
            return None
        return self._to_domain(orm)

    def add(self, notificacion: Notificacion) -> None:
        orm = self._to_orm(notificacion)
        self._session.add(orm)
        # flush explicito: la sesion es autoflush=False y este agregado se
        # suele actualizar (update) en el mismo handler, en la misma sesion.
        self._session.flush()

    def update(self, notificacion: Notificacion) -> None:
        orm = self._session.get(NotificacionORM, str(notificacion.id))
        if orm is None:
            raise ValueError(f"Notificacion {notificacion.id} no encontrada para actualizar")
        orm.estado = notificacion.estado.value
        orm.motivo_fallo = notificacion.motivo_fallo
        orm.canal = notificacion.canal.value
        self._session.add(orm)

    @staticmethod
    def _to_domain(orm: NotificacionORM) -> Notificacion:
        return Notificacion(
            id=uuid.UUID(orm.id),
            destinatario=Destinatario(
                id=orm.destinatario_id,
                nombre=orm.destinatario_nombre,
                contacto=orm.destinatario_contacto,
            ),
            tipo=orm.tipo,
            canal=Canal(orm.canal),
            trabajo_id=orm.trabajo_id,
            asunto=orm.asunto,
            cuerpo=orm.cuerpo,
            estado=EstadoNotificacion(orm.estado),
            motivo_fallo=orm.motivo_fallo,
        )

    @staticmethod
    def _to_orm(notificacion: Notificacion) -> NotificacionORM:
        return NotificacionORM(
            id=str(notificacion.id),
            destinatario_id=notificacion.destinatario.id,
            destinatario_nombre=notificacion.destinatario.nombre,
            destinatario_contacto=notificacion.destinatario.contacto,
            tipo=notificacion.tipo,
            canal=notificacion.canal.value,
            trabajo_id=notificacion.trabajo_id,
            asunto=notificacion.asunto,
            cuerpo=notificacion.cuerpo,
            estado=notificacion.estado.value,
            motivo_fallo=notificacion.motivo_fallo,
        )
