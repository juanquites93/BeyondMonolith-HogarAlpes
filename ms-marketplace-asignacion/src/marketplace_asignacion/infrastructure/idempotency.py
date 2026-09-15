from __future__ import annotations
import json
import uuid
import hashlib
from datetime import datetime
from typing import Optional, Callable, Any

from sqlalchemy.orm import Session

from marketplace_asignacion.infrastructure.orm import IdempotencyKeyORM


class IdempotencyService:
    def __init__(self, session: Session):
        self._session = session

    @staticmethod
    def compute_key(
        command_type: str, payload: dict, correlation_id: Optional[str] = None
    ) -> str:
        data = json.dumps(
            {"cmd": command_type, "payload": payload, "corr": correlation_id},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def check_or_run(
        self,
        key: str,
        command_type: str,
        fn: Callable[[], Any],
    ) -> Any:
        existing = self._session.query(IdempotencyKeyORM).filter_by(key=key).first()
        if existing:
            return existing.response_payload

        result = fn()
        # Serializar resultado (soporta Trabajo o dict)
        serialized = self._serialize_result(result)
        orm = IdempotencyKeyORM(
            id=str(uuid.uuid4()),
            key=key,
            command_type=command_type,
            response_payload=serialized,
            created_at=datetime.utcnow(),
        )
        self._session.add(orm)
        self._session.commit()
        return result

    @staticmethod
    def _serialize_result(result: Any) -> dict:
        if hasattr(result, "id"):
            # Es un Trabajo
            return {
                "trabajo_id": str(result.id),
                "cliente_id": str(result.cliente_id),
                "estado": result.estado.value,
                "proveedor_seleccionado_id": str(result.proveedor_seleccionado_id)
                if result.proveedor_seleccionado_id
                else None,
            }
        if isinstance(result, dict):
            return result
        return {"result": str(result)}
