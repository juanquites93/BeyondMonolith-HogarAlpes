from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List

from generador_cotizacion.domain.events import DomainEvent


class OutboxStore(ABC):
    @abstractmethod
    def store(self, eventos: List[DomainEvent]) -> None:
        raise NotImplementedError
