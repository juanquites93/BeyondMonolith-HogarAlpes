"""Implementación de Unit of Work con SQLAlchemy."""

from __future__ import annotations
from sqlalchemy.orm import Session

from verificacion_acreditacion.application.unit_of_work import UnitOfWork
from verificacion_acreditacion.infrastructure import database as db_module
from verificacion_acreditacion.infrastructure.repositories import (
    SqlAlchemyProveedorRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory=None):
        self.session_factory = session_factory or db_module.SessionLocal
        self.session: Session | None = None
        self.proveedores: SqlAlchemyProveedorRepository | None = None

    def __enter__(self):
        self.session = self.session_factory()
        self.proveedores = SqlAlchemyProveedorRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.session.close()
        self.session = None
        self.proveedores = None

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
