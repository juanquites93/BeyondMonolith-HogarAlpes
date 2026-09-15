from __future__ import annotations
from sqlalchemy.orm import Session

from generador_cotizacion.application.unit_of_work import UnitOfWork
from generador_cotizacion.infrastructure import database as db_module
from generador_cotizacion.infrastructure.repositories import (
    SqlAlchemyCotizacionRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory=None):
        self.session_factory = session_factory or db_module.SessionLocal
        self.session: Session | None = None
        self.cotizaciones: SqlAlchemyCotizacionRepository | None = None

    def __enter__(self):
        self.session = self.session_factory()
        self.cotizaciones = SqlAlchemyCotizacionRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.session.close()
        self.session = None
        self.cotizaciones = None

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
