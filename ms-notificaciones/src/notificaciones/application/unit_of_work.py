from __future__ import annotations
from abc import ABC, abstractmethod

from notificaciones.domain.repository import NotificacionRepository


class UnitOfWork(ABC):
    notificaciones: NotificacionRepository

    def __enter__(self) -> UnitOfWork:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError
