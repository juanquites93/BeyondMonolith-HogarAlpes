from __future__ import annotations
import logging

from notificaciones.domain.services import PasarelaPort
from notificaciones.domain.value_objects import Canal

logger = logging.getLogger(__name__)


class PasarelaSimulada(PasarelaPort):
    """Adaptador simulado de envio (email/SMS).

    En producción se reemplazaría por un proveedor real (SendGrid, Twilio).
    """

    def enviar(self, canal: Canal, contacto: str, asunto: str, cuerpo: str) -> bool:
        logger.info(
            "[PASARELA-SIMULADA] Enviando notificacion",
            extra={"canal": canal.value, "contacto": contacto, "asunto": asunto},
        )
        return True
