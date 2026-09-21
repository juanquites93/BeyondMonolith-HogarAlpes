"""Agregado Saga con reglas de transición de estado."""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from ms_orquestador.application.saga_state import SagaState


class SagaTransitionError(Exception):
    pass


@dataclass
class Saga:
    saga_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    trabajo_id: Optional[str] = None
    proveedor_id: Optional[str] = None
    current_state: str = field(default=SagaState.INICIADA.value)
    retry_count: int = 0
    last_event_type: Optional[str] = None
    last_error: Optional[str] = None
    payload_context: dict = field(default_factory=dict)
    compensated_steps: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def start(
        self,
        correlation_id: str,
        trabajo_id: str,
        proveedor_id: str,
        payload_context: dict,
    ) -> None:
        self.correlation_id = correlation_id
        self.trabajo_id = trabajo_id
        self.proveedor_id = proveedor_id
        self.payload_context = payload_context or {}
        self._transition_to(SagaState.PROVEEDOR_SELECCIONADO)

    def start_verification(self) -> None:
        self._transition_to(SagaState.VERIFICACION_EN_PROCESO)

    def mark_verification_pending(self, reason: str) -> None:
        self._transition_to(SagaState.VERIFICACION_PENDIENTE)
        self.last_error = reason

    def wait_for_retry(self) -> None:
        self._transition_to(SagaState.ESPERANDO_REINTENTO)

    def retry(self) -> None:
        self.retry_count += 1
        self._transition_to(SagaState.VERIFICACION_EN_PROCESO)

    def mark_provider_accredited(self) -> None:
        self.last_error = None
        self._transition_to(SagaState.PROVEEDOR_ACREDITADO)

    def start_quotation(self) -> None:
        self._transition_to(SagaState.COTIZACION_EN_PROCESO)

    def mark_quotation_generated(self) -> None:
        self._transition_to(SagaState.COTIZACION_GENERADA)

    def start_notification(self) -> None:
        self._transition_to(SagaState.NOTIFICACION_EN_PROCESO)

    def mark_completed(self) -> None:
        self._transition_to(SagaState.COMPLETADA)

    def mark_failed(self, reason: str) -> None:
        self.last_error = reason
        self._transition_to(SagaState.FALLIDA)

    def start_compensation(self, reason: str) -> None:
        self.last_error = reason
        self.compensated_steps = []
        self._transition_to(SagaState.COMPENSANDO)

    def mark_step_compensated(self, event_type: str) -> None:
        if event_type not in self.compensated_steps:
            self.compensated_steps.append(event_type)
        self.updated_at = datetime.utcnow()

    def mark_compensated(self) -> None:
        self._transition_to(SagaState.COMPENSADA)

    def _transition_to(self, new_state: SagaState) -> None:
        allowed = _TRANSITIONS.get(self.current_state, set())
        if new_state.value not in allowed:
            raise SagaTransitionError(
                f"Transición no permitida de {self.current_state} a {new_state.value}"
            )
        self.current_state = new_state.value
        self.updated_at = datetime.utcnow()


_TRANSITIONS = {
    SagaState.INICIADA.value: {
        SagaState.PROVEEDOR_SELECCIONADO.value,
    },
    SagaState.PROVEEDOR_SELECCIONADO.value: {
        SagaState.VERIFICACION_EN_PROCESO.value,
        SagaState.FALLIDA.value,
    },
    SagaState.VERIFICACION_EN_PROCESO.value: {
        SagaState.VERIFICACION_PENDIENTE.value,
        SagaState.PROVEEDOR_ACREDITADO.value,
        SagaState.FALLIDA.value,
    },
    SagaState.VERIFICACION_PENDIENTE.value: {
        SagaState.ESPERANDO_REINTENTO.value,
        SagaState.VERIFICACION_EN_PROCESO.value,
        SagaState.FALLIDA.value,
    },
    SagaState.ESPERANDO_REINTENTO.value: {
        SagaState.VERIFICACION_EN_PROCESO.value,
        SagaState.PROVEEDOR_ACREDITADO.value,
        SagaState.FALLIDA.value,
    },
    SagaState.PROVEEDOR_ACREDITADO.value: {
        SagaState.COTIZACION_EN_PROCESO.value,
        SagaState.FALLIDA.value,
    },
    SagaState.COTIZACION_EN_PROCESO.value: {
        SagaState.COTIZACION_GENERADA.value,
        SagaState.FALLIDA.value,
    },
    SagaState.COTIZACION_GENERADA.value: {
        SagaState.NOTIFICACION_EN_PROCESO.value,
        SagaState.FALLIDA.value,
    },
    SagaState.NOTIFICACION_EN_PROCESO.value: {
        SagaState.COMPLETADA.value,
        SagaState.FALLIDA.value,
        SagaState.COMPENSANDO.value,
    },
    SagaState.COMPENSANDO.value: {
        SagaState.COMPENSADA.value,
        SagaState.FALLIDA.value,
    },
    SagaState.COMPLETADA.value: set(),
    SagaState.FALLIDA.value: set(),
    SagaState.COMPENSADA.value: set(),
}
