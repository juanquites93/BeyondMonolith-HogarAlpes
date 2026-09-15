from __future__ import annotations
import uuid
from abc import ABC, abstractmethod
from typing import Optional

from marketplace_asignacion.domain.model import Trabajo


class TrabajoRepository(ABC):
    @abstractmethod
    def get(self, id: uuid.UUID) -> Optional[Trabajo]:
        raise NotImplementedError

    @abstractmethod
    def add(self, trabajo: Trabajo) -> None:
        raise NotImplementedError

    @abstractmethod
    def update(self, trabajo: Trabajo) -> None:
        raise NotImplementedError
