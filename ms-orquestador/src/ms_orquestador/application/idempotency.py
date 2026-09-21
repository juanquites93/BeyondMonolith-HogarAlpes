"""Servicio de idempotencia para el orquestador."""

from __future__ import annotations
import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Optional, Callable, Any

from sqlalchemy.orm import Session

from ms_orquestador.infrastructure.orm import IdempotencyKeyORM

logger = logging.getLogger(__name__)


class IdempotencyService:
    def __init__(self, session: Session):
        self._session = session

    @staticmethod
    def compute_key(
        message_type: str, payload: dict, correlation_id: Optional[str] = None
    ) -> str:
        data = json.dumps(
            {"type": message_type, "payload": payload, "corr": correlation_id},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def has_processed(self, key: str) -> bool:
        return (
            self._session.query(IdempotencyKeyORM.id).filter_by(key=key).first()
            is not None
        )

    def check_or_run(
        self,
        key: str,
        message_type: str,
        fn: Callable[[], Any],
    ) -> Any:
        existing = self._session.query(IdempotencyKeyORM).filter_by(key=key).first()
        if existing:
            logger.info(
                "Mensaje ya procesado (idempotencia)",
                extra={"key": key, "message_type": message_type},
            )
            return existing.response_payload

        result = fn()
        serialized = self._serialize_result(result)
        orm = IdempotencyKeyORM(
            id=str(uuid.uuid4()),
            key=key,
            command_type=message_type,
            response_payload=serialized,
            created_at=datetime.utcnow(),
        )
        self._session.add(orm)
        self._session.commit()
        return result

    @staticmethod
    def _serialize_result(result: Any) -> dict:
        if isinstance(result, dict):
            return result
        if result is None:
            return {"result": "ok"}
        return {"result": str(result)}
