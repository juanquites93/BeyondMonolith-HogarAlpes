from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List

from marketplace_asignacion.domain.events import DomainEvent


class OutboxStore(ABC):
    @abstractmethod
    def store(self, eventos: List[DomainEvent]) -> None:
        raise NotImplementedError
