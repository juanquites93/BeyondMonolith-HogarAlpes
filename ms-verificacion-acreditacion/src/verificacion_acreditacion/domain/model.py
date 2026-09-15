"""Modelo de dominio: Proveedor, Verificación, Acreditación."""

from __future__ import annotations
import uuid
from typing import List, Optional
from dataclasses import dataclass, field

from verificacion_acreditacion.domain.value_objects import (
    EstadoVerificacion,
    EstadoAcreditacion,
    Evidencia,
)
from verificacion_acreditacion.domain.events import (
    DomainEvent,
    VerificacionProveedorIniciada,
    VerificacionProveedorAprobada,
    VerificacionProveedorRechazada,
    ProveedorAcreditado,
    ProveedorNoAcreditado,
)
from verificacion_acreditacion.domain.exceptions import (
    EstadoInvalidoError,
    ProveedorNoVerificadoError,
    VerificacionYaResueltaError,
)


@dataclass
class Proveedor:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    nombre: str = ""
    estado_verificacion: EstadoVerificacion = EstadoVerificacion.PENDIENTE
    estado_acreditacion: EstadoAcreditacion = EstadoAcreditacion.NO_ACREDITADO
    _eventos: List[DomainEvent] = field(default_factory=list, repr=False)

    @property
    def eventos(self) -> List[DomainEvent]:
        return list(self._eventos)

    def limpiar_eventos(self) -> None:
        self._eventos.clear()

    def _aplicar_evento(self, evento: DomainEvent) -> None:
        evento.aggregate_id = self.id
        self._eventos.append(evento)

    def iniciar_verificacion(self, correlation_id: Optional[str] = None) -> None:
        if self.estado_verificacion != EstadoVerificacion.PENDIENTE:
            raise EstadoInvalidoError(
                f"No se puede iniciar verificación en estado {self.estado_verificacion.value}"
            )
        self.estado_verificacion = EstadoVerificacion.PENDIENTE
        evento = VerificacionProveedorIniciada(
            verificacion_id=uuid.uuid4(),
            proveedor_id=self.id,
            correlation_id=correlation_id,
        )
        self._aplicar_evento(evento)

    def aprobar_verificacion(self, correlation_id: Optional[str] = None) -> None:
        if self.estado_verificacion == EstadoVerificacion.APROBADA:
            raise VerificacionYaResueltaError("La verificación ya fue aprobada.")
        if self.estado_verificacion == EstadoVerificacion.RECHAZADA:
            raise VerificacionYaResueltaError("La verificación ya fue rechazada.")
        self.estado_verificacion = EstadoVerificacion.APROBADA
        evento = VerificacionProveedorAprobada(
            verificacion_id=uuid.uuid4(),
            proveedor_id=self.id,
            correlation_id=correlation_id,
        )
        self._aplicar_evento(evento)

    def rechazar_verificacion(
        self, motivo: Optional[str] = None, correlation_id: Optional[str] = None
    ) -> None:
        if self.estado_verificacion == EstadoVerificacion.APROBADA:
            raise VerificacionYaResueltaError("La verificación ya fue aprobada.")
        if self.estado_verificacion == EstadoVerificacion.RECHAZADA:
            raise VerificacionYaResueltaError("La verificación ya fue rechazada.")
        self.estado_verificacion = EstadoVerificacion.RECHAZADA
        evento = VerificacionProveedorRechazada(
            verificacion_id=uuid.uuid4(),
            proveedor_id=self.id,
            motivo=motivo,
            correlation_id=correlation_id,
        )
        self._aplicar_evento(evento)

    def acreditar(self, correlation_id: Optional[str] = None) -> None:
        if self.estado_verificacion != EstadoVerificacion.APROBADA:
            raise ProveedorNoVerificadoError(
                "No se puede acreditar un proveedor sin verificación aprobada"
            )
        self.estado_acreditacion = EstadoAcreditacion.ACREDITADO
        evento = ProveedorAcreditado(
            proveedor_id=self.id,
            acreditacion_id=uuid.uuid4(),
            correlation_id=correlation_id,
        )
        self._aplicar_evento(evento)

    def rechazar_acreditacion(
        self, motivo: Optional[str] = None, correlation_id: Optional[str] = None
    ) -> None:
        self.estado_acreditacion = EstadoAcreditacion.RECHAZADA
        evento = ProveedorNoAcreditado(
            proveedor_id=self.id,
            acreditacion_id=uuid.uuid4(),
            motivo=motivo,
            correlation_id=correlation_id,
        )
        self._aplicar_evento(evento)
