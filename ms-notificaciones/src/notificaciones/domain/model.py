from __future__ import annotations
import uuid
from typing import List, Optional
from dataclasses import dataclass, field

from notificaciones.domain.events import (
    DomainEvent,
    NotificacionSolicitada,
    NotificacionEnviada,
    NotificacionFallida,
)
from notificaciones.domain.value_objects import (
    Destinatario,
    Canal,
    EstadoNotificacion,
)


class EstadoInvalidoError(Exception):
    pass


@dataclass
class Notificacion:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    destinatario: Optional[Destinatario] = None
    tipo: str = ""
    canal: Canal = Canal.EMAIL
    trabajo_id: Optional[str] = None
    asunto: str = ""
    cuerpo: str = ""
    estado: EstadoNotificacion = EstadoNotificacion.PENDIENTE
    motivo_fallo: Optional[str] = None
    _eventos: List[DomainEvent] = field(default_factory=list, repr=False)

    @property
    def eventos(self) -> List[DomainEvent]:
        return list(self._eventos)

    def limpiar_eventos(self) -> None:
        self._eventos.clear()

    def _aplicar_evento(self, evento: DomainEvent) -> None:
        evento.aggregate_id = self.id
        self._eventos.append(evento)

    def solicitar(self, correlation_id: Optional[str] = None) -> None:
        if self.estado != EstadoNotificacion.PENDIENTE:
            raise EstadoInvalidoError(
                f"No se puede solicitar una notificacion en estado {self.estado.value}"
            )
        evento = NotificacionSolicitada(
            notificacion_id=self.id,
            destinatario_id=self.destinatario.id if self.destinatario else None,
            tipo=self.tipo,
            canal=self.canal.value,
            correlation_id=correlation_id,
        )
        self._aplicar_evento(evento)

    def marcar_enviada(self, correlation_id: Optional[str] = None) -> None:
        if self.estado != EstadoNotificacion.PENDIENTE:
            raise EstadoInvalidoError(
                f"No se puede marcar como enviada una notificacion en estado {self.estado.value}"
            )
        self.estado = EstadoNotificacion.ENVIADA
        evento = NotificacionEnviada(
            notificacion_id=self.id,
            destinatario_id=self.destinatario.id if self.destinatario else None,
            canal=self.canal.value,
            correlation_id=correlation_id,
        )
        self._aplicar_evento(evento)

    def marcar_fallida(self, motivo: str, correlation_id: Optional[str] = None) -> None:
        if self.estado != EstadoNotificacion.PENDIENTE:
            raise EstadoInvalidoError(
                f"No se puede marcar como fallida una notificacion en estado {self.estado.value}"
            )
        self.estado = EstadoNotificacion.FALLIDA
        self.motivo_fallo = motivo
        evento = NotificacionFallida(
            notificacion_id=self.id,
            destinatario_id=self.destinatario.id if self.destinatario else None,
            canal=self.canal.value,
            motivo=motivo,
            correlation_id=correlation_id,
        )
        self._aplicar_evento(evento)
