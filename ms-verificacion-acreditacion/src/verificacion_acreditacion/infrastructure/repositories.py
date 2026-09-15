"""Implementación de repositorios con SQLAlchemy."""

from __future__ import annotations
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from verificacion_acreditacion.domain.model import Proveedor
from verificacion_acreditacion.domain.repository import ProveedorRepository
from verificacion_acreditacion.domain.value_objects import (
    EstadoVerificacion,
    EstadoAcreditacion,
)
from verificacion_acreditacion.infrastructure.orm import ProveedorORM


class SqlAlchemyProveedorRepository(ProveedorRepository):
    def __init__(self, session: Session):
        self._session = session

    def get(self, id: uuid.UUID) -> Optional[Proveedor]:
        orm = self._session.get(ProveedorORM, str(id))
        if orm is None:
            return None
        return self._to_domain(orm)

    def add(self, proveedor: Proveedor) -> None:
        orm = self._to_orm(proveedor)
        self._session.add(orm)
        self._session.flush()

    def update(self, proveedor: Proveedor) -> None:
        orm = self._session.get(ProveedorORM, str(proveedor.id))
        if orm is None:
            raise ValueError(f"Proveedor {proveedor.id} no encontrado")
        orm.estado_verificacion = proveedor.estado_verificacion.value
        orm.estado_acreditacion = proveedor.estado_acreditacion.value
        self._session.add(orm)

    @staticmethod
    def _to_domain(orm: ProveedorORM) -> Proveedor:
        return Proveedor(
            id=uuid.UUID(orm.id),
            nombre=orm.nombre,
            estado_verificacion=EstadoVerificacion(orm.estado_verificacion),
            estado_acreditacion=EstadoAcreditacion(orm.estado_acreditacion),
        )

    @staticmethod
    def _to_orm(proveedor: Proveedor) -> ProveedorORM:
        return ProveedorORM(
            id=str(proveedor.id),
            nombre=proveedor.nombre,
            estado_verificacion=proveedor.estado_verificacion.value,
            estado_acreditacion=proveedor.estado_acreditacion.value,
        )
