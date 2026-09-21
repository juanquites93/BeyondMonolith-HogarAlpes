from __future__ import annotations
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from generador_cotizacion.domain.model import Cotizacion
from generador_cotizacion.domain.repository import CotizacionRepository
from generador_cotizacion.domain.value_objects import EstadoCotizacion
from generador_cotizacion.infrastructure.orm import CotizacionORM


class MySQLCotizacionRepository(CotizacionRepository):
    """Implementación del puerto CotizacionRepository sobre MySQL.

    Demuestra que la implementación con PostgreSQL (SqlAlchemyCotizacionRepository)
    puede sustituirse por MySQL sin tocar el dominio ni la aplicación, ya que
    ambas se apoyan en los mismos modelos ORM de SQLAlchemy.
    """

    def __init__(self, session: Session):
        self._session = session

    def get(self, id: uuid.UUID) -> Optional[Cotizacion]:
        orm = self._session.get(CotizacionORM, str(id))
        if orm is None:
            return None
        return self._to_domain(orm)

    def list(self, trabajo_id: Optional[uuid.UUID] = None) -> List[Cotizacion]:
        query = self._session.query(CotizacionORM)
        if trabajo_id is not None:
            query = query.filter(CotizacionORM.trabajo_id == str(trabajo_id))
        return [self._to_domain(orm) for orm in query.all()]

    def add(self, cotizacion: Cotizacion) -> None:
        orm = self._to_orm(cotizacion)
        self._session.add(orm)

    def update(self, cotizacion: Cotizacion) -> None:
        orm = self._session.get(CotizacionORM, str(cotizacion.id))
        if orm is None:
            raise ValueError(f"Cotización {cotizacion.id} no encontrada para actualizar")
        orm.proveedor_id = str(cotizacion.proveedor_id) if cotizacion.proveedor_id else None
        orm.monto = cotizacion.monto
        orm.moneda = cotizacion.moneda
        orm.descripcion = cotizacion.descripcion
        orm.estado = cotizacion.estado.value
        orm.fecha_validez = cotizacion.fecha_validez
        self._session.add(orm)

    def delete(self, id: uuid.UUID) -> None:
        orm = self._session.get(CotizacionORM, str(id))
        if orm is None:
            raise ValueError(f"Cotización {id} no encontrada para eliminar")
        self._session.delete(orm)

    @staticmethod
    def _to_domain(orm: CotizacionORM) -> Cotizacion:
        return Cotizacion(
            id=uuid.UUID(orm.id),
            trabajo_id=uuid.UUID(orm.trabajo_id),
            proveedor_id=uuid.UUID(orm.proveedor_id) if orm.proveedor_id else None,
            monto=orm.monto,
            moneda=orm.moneda,
            descripcion=orm.descripcion,
            estado=EstadoCotizacion(orm.estado),
            fecha_solicitud=orm.fecha_solicitud,
            fecha_validez=orm.fecha_validez,
        )

    @staticmethod
    def _to_orm(cotizacion: Cotizacion) -> CotizacionORM:
        return CotizacionORM(
            id=str(cotizacion.id),
            trabajo_id=str(cotizacion.trabajo_id),
            proveedor_id=str(cotizacion.proveedor_id) if cotizacion.proveedor_id else None,
            monto=cotizacion.monto,
            moneda=cotizacion.moneda,
            descripcion=cotizacion.descripcion,
            estado=cotizacion.estado.value,
            fecha_solicitud=cotizacion.fecha_solicitud,
            fecha_validez=cotizacion.fecha_validez,
        )
