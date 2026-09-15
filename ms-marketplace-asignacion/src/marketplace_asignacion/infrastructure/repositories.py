from __future__ import annotations
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from marketplace_asignacion.domain.model import Trabajo
from marketplace_asignacion.domain.repository import TrabajoRepository
from marketplace_asignacion.domain.value_objects import Ubicacion, Alcance
from marketplace_asignacion.infrastructure.orm import TrabajoORM


class SqlAlchemyTrabajoRepository(TrabajoRepository):
    def __init__(self, session: Session):
        self._session = session

    def get(self, id: uuid.UUID) -> Optional[Trabajo]:
        orm = self._session.get(TrabajoORM, str(id))
        if orm is None:
            return None
        return self._to_domain(orm)

    def add(self, trabajo: Trabajo) -> None:
        orm = self._to_orm(trabajo)
        self._session.add(orm)

    def update(self, trabajo: Trabajo) -> None:
        orm = self._session.get(TrabajoORM, str(trabajo.id))
        if orm is None:
            raise ValueError(f"Trabajo {trabajo.id} no encontrado para actualizar")
        orm.estado = trabajo.estado.value
        orm.proveedor_seleccionado_id = (
            str(trabajo.proveedor_seleccionado_id)
            if trabajo.proveedor_seleccionado_id
            else None
        )
        if trabajo.alcance:
            orm.descripcion = trabajo.alcance.descripcion
            orm.categoria = trabajo.alcance.categoria
            orm.notas = trabajo.alcance.notas
        self._session.add(orm)

    @staticmethod
    def _to_domain(orm: TrabajoORM) -> Trabajo:
        from marketplace_asignacion.domain.model import Trabajo as DomainTrabajo
        from marketplace_asignacion.domain.value_objects import EstadoTrabajo

        trabajo = DomainTrabajo(
            id=uuid.UUID(orm.id),
            cliente_id=uuid.UUID(orm.cliente_id),
            ubicacion=Ubicacion(
                direccion=orm.direccion,
                ciudad=orm.ciudad,
                pais=orm.pais,
                codigo_postal=orm.codigo_postal,
            ),
            alcance=Alcance(
                descripcion=orm.descripcion,
                categoria=orm.categoria,
                notas=orm.notas,
            ),
            estado=EstadoTrabajo(orm.estado),
            proveedor_seleccionado_id=uuid.UUID(orm.proveedor_seleccionado_id)
            if orm.proveedor_seleccionado_id
            else None,
        )
        return trabajo

    @staticmethod
    def _to_orm(trabajo: Trabajo) -> TrabajoORM:
        return TrabajoORM(
            id=str(trabajo.id),
            cliente_id=str(trabajo.cliente_id),
            direccion=trabajo.ubicacion.direccion if trabajo.ubicacion else "",
            ciudad=trabajo.ubicacion.ciudad if trabajo.ubicacion else "",
            pais=trabajo.ubicacion.pais if trabajo.ubicacion else "",
            codigo_postal=trabajo.ubicacion.codigo_postal
            if trabajo.ubicacion
            else None,
            descripcion=trabajo.alcance.descripcion if trabajo.alcance else "",
            categoria=trabajo.alcance.categoria if trabajo.alcance else "",
            notas=trabajo.alcance.notas if trabajo.alcance else None,
            estado=trabajo.estado.value,
            proveedor_seleccionado_id=str(trabajo.proveedor_seleccionado_id)
            if trabajo.proveedor_seleccionado_id
            else None,
        )
