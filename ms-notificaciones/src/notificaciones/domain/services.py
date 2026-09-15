from __future__ import annotations
from abc import ABC, abstractmethod

from notificaciones.domain.value_objects import Canal


class PasarelaPort(ABC):
    """Puerto para enviar la notificacion por un canal (anti-corruption layer)."""

    @abstractmethod
    def enviar(self, canal: Canal, contacto: str, asunto: str, cuerpo: str) -> bool:
        raise NotImplementedError
