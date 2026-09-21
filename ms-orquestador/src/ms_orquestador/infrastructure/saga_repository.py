"""Repositorio SQLAlchemy para persistir Sagas y su log."""

from __future__ import annotations
import json
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from ms_orquestador.application.saga import Saga
from ms_orquestador.infrastructure.orm import SagaORM, SagaLogORM

logger = logging.getLogger(__name__)


class SagaRepository:
    def __init__(self, session: Session):
        self._session = session

    def get(self, saga_id: str) -> Optional[Saga]:
        orm = self._session.get(SagaORM, saga_id)
        if orm is None:
            return None
        return self._to_domain(orm)

    def get_by_trabajo(self, trabajo_id: str) -> Optional[Saga]:
        orm = (
            self._session.query(SagaORM)
            .filter(SagaORM.trabajo_id == trabajo_id)
            .order_by(SagaORM.created_at.desc())
            .first()
        )
        if orm is None:
            return None
        return self._to_domain(orm)

    def list_active(self) -> List[Saga]:
        rows = (
            self._session.query(SagaORM)
            .filter(SagaORM.current_state.notin_(["COMPLETADA", "FALLIDA"]))
            .all()
        )
        return [self._to_domain(row) for row in rows]

    def save(self, saga: Saga) -> None:
        existing = self._session.get(SagaORM, saga.saga_id)
        if existing:
            existing.correlation_id = saga.correlation_id
            existing.trabajo_id = saga.trabajo_id
            existing.proveedor_id = saga.proveedor_id
            existing.current_state = saga.current_state
            existing.retry_count = saga.retry_count
            existing.last_event_type = saga.last_event_type
            existing.last_error = saga.last_error
            existing.payload_context = saga.payload_context
            existing.compensated_steps = saga.compensated_steps
            existing.updated_at = datetime.utcnow()
        else:
            orm = SagaORM(
                saga_id=saga.saga_id,
                correlation_id=saga.correlation_id,
                trabajo_id=saga.trabajo_id,
                proveedor_id=saga.proveedor_id,
                current_state=saga.current_state,
                retry_count=saga.retry_count,
                last_event_type=saga.last_event_type,
                last_error=saga.last_error,
                payload_context=saga.payload_context,
                compensated_steps=saga.compensated_steps,
                created_at=saga.created_at,
                updated_at=saga.updated_at,
            )
            self._session.add(orm)
        self._session.flush()

    def log_event(
        self,
        saga_id: str,
        correlation_id: Optional[str],
        message_id: Optional[str],
        causation_id: Optional[str],
        message_type: str,
        producer: str,
        status: str,
        payload: dict,
        error_message: Optional[str] = None,
    ) -> None:
        orm = SagaLogORM(
            saga_id=saga_id,
            correlation_id=correlation_id,
            message_id=message_id,
            causation_id=causation_id,
            message_type=message_type,
            producer=producer,
            status=status,
            payload=payload,
            error_message=error_message,
            occurred_at=datetime.utcnow(),
        )
        self._session.add(orm)

    @staticmethod
    def _to_domain(orm: SagaORM) -> Saga:
        saga = Saga(
            saga_id=orm.saga_id,
            correlation_id=orm.correlation_id,
            trabajo_id=orm.trabajo_id,
            proveedor_id=orm.proveedor_id,
            current_state=orm.current_state,
            retry_count=orm.retry_count,
            last_event_type=orm.last_event_type,
            last_error=orm.last_error,
            payload_context=orm.payload_context or {},
            compensated_steps=orm.compensated_steps or [],
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
        return saga
