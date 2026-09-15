from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Any


class OutboxStore(ABC):
    @abstractmethod
    def store(self, eventos: List[Any]) -> None:
        raise NotImplementedError
