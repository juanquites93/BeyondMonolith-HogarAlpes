from __future__ import annotations
import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

from generador_cotizacion.domain.model import Cotizacion


class CotizacionRepository(ABC):
    @abstractmethod
    def get(self, id: uuid.UUID) -> Optional[Cotizacion]:
        raise NotImplementedError

    @abstractmethod
    def list(self, trabajo_id: Optional[uuid.UUID] = None) -> List[Cotizacion]:
        raise NotImplementedError

    @abstractmethod
    def add(self, cotizacion: Cotizacion) -> None:
        raise NotImplementedError

    @abstractmethod
    def update(self, cotizacion: Cotizacion) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, id: uuid.UUID) -> None:
        raise NotImplementedError
