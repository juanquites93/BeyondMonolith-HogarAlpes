from __future__ import annotations
import uuid
from typing import Optional

from pydantic import BaseModel


class NotificacionResponse(BaseModel):
    notificacion_id: uuid.UUID
    destinatario_id: str
    tipo: str
    canal: str
    trabajo_id: Optional[str] = None
    estado: str
    motivo_fallo: Optional[str] = None

    class Config:
        from_attributes = True
