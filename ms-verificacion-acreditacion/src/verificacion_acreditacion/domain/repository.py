"""Puertos de repositorio (abstractos)."""

from __future__ import annotations
import uuid
from abc import ABC, abstractmethod
from typing import Optional

from verificacion_acreditacion.domain.model import Proveedor


class ProveedorRepository(ABC):
    @abstractmethod
    def get(self, id: uuid.UUID) -> Optional[Proveedor]:
        raise NotImplementedError

    @abstractmethod
    def add(self, proveedor: Proveedor) -> None:
        raise NotImplementedError

    @abstractmethod
    def update(self, proveedor: Proveedor) -> None:
        raise NotImplementedError
