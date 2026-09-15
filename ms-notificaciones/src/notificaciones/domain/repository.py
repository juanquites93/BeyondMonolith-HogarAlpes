from __future__ import annotations
import uuid
from abc import ABC, abstractmethod
from typing import Optional

from notificaciones.domain.model import Notificacion


class NotificacionRepository(ABC):
    @abstractmethod
    def get(self, id: uuid.UUID) -> Optional[Notificacion]:
        raise NotImplementedError

    @abstractmethod
    def add(self, notificacion: Notificacion) -> None:
        raise NotImplementedError

    @abstractmethod
    def update(self, notificacion: Notificacion) -> None:
        raise NotImplementedError
