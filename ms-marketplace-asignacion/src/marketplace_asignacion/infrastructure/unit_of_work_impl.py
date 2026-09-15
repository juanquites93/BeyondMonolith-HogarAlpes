from __future__ import annotations
from sqlalchemy.orm import Session

from marketplace_asignacion.application.unit_of_work import UnitOfWork
from marketplace_asignacion.infrastructure import database as db_module
from marketplace_asignacion.infrastructure.repositories import (
    SqlAlchemyTrabajoRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory=None):
        self.session_factory = session_factory or db_module.SessionLocal
        self.session: Session | None = None
        self.trabajos: SqlAlchemyTrabajoRepository | None = None

    def __enter__(self):
        self.session = self.session_factory()
        self.trabajos = SqlAlchemyTrabajoRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.session.close()
        self.session = None
        self.trabajos = None

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
