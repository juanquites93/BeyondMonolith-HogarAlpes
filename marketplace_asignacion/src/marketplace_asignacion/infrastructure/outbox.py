from __future__ import annotations
import json
import uuid
import dataclasses
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from marketplace_asignacion.application.outbox_port import OutboxStore
from marketplace_asignacion.domain.events import DomainEvent
from marketplace_asignacion.infrastructure.orm import OutboxORM


class SqlAlchemyOutboxStore(OutboxStore):
    def __init__(self, session: Session | None = None):
        # session puede ser inyectada o asignada externamente antes de store()
        self._session = session

    def bind(self, session: Session) -> None:
        self._session = session

    def store(self, eventos: List[DomainEvent]) -> None:
        if self._session is None:
            raise RuntimeError(
                "OutboxStore requiere una sesión de base de datos activa"
            )
        for evento in eventos:
            payload = self._serialize(evento)
            orm = OutboxORM(
                id=str(uuid.uuid4()),
                aggregate_type="Trabajo",
                aggregate_id=str(evento.aggregate_id) if evento.aggregate_id else None,
                event_type=evento.event_type,
                version=evento.version,
                payload=payload,
                occurred_at=evento.occurred_at,
                correlation_id=evento.correlation_id,
            )
            self._session.add(orm)

    @staticmethod
    def _serialize(evento: DomainEvent) -> dict:
        # Serialización manual controlada para evitar problemas con UUID/datetime
        base = {
            "event_id": str(evento.event_id),
            "event_type": evento.event_type,
            "version": evento.version,
            "occurred_at": evento.occurred_at.isoformat()
            if evento.occurred_at
            else None,
            "correlation_id": evento.correlation_id,
            "aggregate_id": str(evento.aggregate_id) if evento.aggregate_id else None,
        }
        # Extender según tipo concreto usando campos conocidos
        if hasattr(evento, "trabajo_id"):
            base["trabajo_id"] = str(evento.trabajo_id) if evento.trabajo_id else None
        if hasattr(evento, "cliente_id"):
            base["cliente_id"] = str(evento.cliente_id) if evento.cliente_id else None
        if hasattr(evento, "ubicacion") and evento.ubicacion:
            base["ubicacion"] = dataclasses.asdict(evento.ubicacion)
        if hasattr(evento, "alcance") and evento.alcance:
            base["alcance"] = dataclasses.asdict(evento.alcance)
        if hasattr(evento, "proveedor_id"):
            base["proveedor_id"] = (
                str(evento.proveedor_id) if evento.proveedor_id else None
            )
        if hasattr(evento, "proveedores_ids"):
            base["proveedores_ids"] = [str(p) for p in evento.proveedores_ids]
        if hasattr(evento, "publicado_en"):
            base["publicado_en"] = (
                evento.publicado_en.isoformat() if evento.publicado_en else None
            )
        if hasattr(evento, "seleccionado_en"):
            base["seleccionado_en"] = (
                evento.seleccionado_en.isoformat() if evento.seleccionado_en else None
            )
        if hasattr(evento, "nuevo_alcance") and evento.nuevo_alcance:
            base["nuevo_alcance"] = dataclasses.asdict(evento.nuevo_alcance)
        if hasattr(evento, "razon"):
            base["razon"] = evento.razon
        return base
