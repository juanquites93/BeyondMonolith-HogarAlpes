"""Unit of Work (puerto)."""

from __future__ import annotations
from abc import ABC, abstractmethod

from verificacion_acreditacion.domain.repository import ProveedorRepository


class UnitOfWork(ABC):
    proveedores: ProveedorRepository

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
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
