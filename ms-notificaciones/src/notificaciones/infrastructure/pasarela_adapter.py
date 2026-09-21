from __future__ import annotations
import logging

from notificaciones.domain.services import PasarelaPort
from notificaciones.domain.value_objects import Canal

logger = logging.getLogger(__name__)


class PasarelaSimulada(PasarelaPort):
    """Adaptador simulado de envio (email/SMS).

    En producción se reemplazaría por un proveedor real (SendGrid, Twilio).
    """

    _forzar_fallo = False

    @classmethod
    def forzar_fallo(cls, activo: bool = True) -> None:
        cls._forzar_fallo = activo

    @classmethod
    def debe_fallar(cls) -> bool:
        return cls._forzar_fallo

    def enviar(self, canal: Canal, contacto: str, asunto: str, cuerpo: str) -> bool:
        if self._forzar_fallo:
            logger.warning(
                "[PASARELA-SIMULADA] Fallo simulado del proveedor de notificaciones",
                extra={"canal": canal.value, "contacto": contacto, "asunto": asunto},
            )
            return False
        logger.info(
            "[PASARELA-SIMULADA] Enviando notificacion",
            extra={"canal": canal.value, "contacto": contacto, "asunto": asunto},
        )
        return True
