from __future__ import annotations
import json
import uuid
import dataclasses
from datetime import datetime
from typing import List, Any

from sqlalchemy.orm import Session

from marketplace_asignacion.application.outbox_port import OutboxStore
from marketplace_asignacion.infrastructure.orm import OutboxORM


class SqlAlchemyOutboxStore(OutboxStore):
    def __init__(self, session: Session | None = None):
        # session puede ser inyectada o asignada externamente antes de store()
        self._session = session

    def bind(self, session: Session) -> None:
        self._session = session

    def store(self, eventos: List[Any]) -> None:
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
    def _serialize(evento: Any) -> dict:
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
        # ── Campos de eventos de dominio ───────────────────────────
        if hasattr(evento, "trabajo_id"):
            base["trabajo_id"] = str(evento.trabajo_id) if evento.trabajo_id else None
        if hasattr(evento, "cliente_id"):
            base["cliente_id"] = str(evento.cliente_id) if evento.cliente_id else None
        if hasattr(evento, "ubicacion") and evento.ubicacion:
            if hasattr(evento.ubicacion, "direccion"):
                base["ubicacion"] = dataclasses.asdict(evento.ubicacion)
            else:
                base["ubicacion"] = evento.ubicacion
        if hasattr(evento, "alcance") and evento.alcance:
            if hasattr(evento.alcance, "descripcion"):
                base["alcance"] = dataclasses.asdict(evento.alcance)
            else:
                base["alcance"] = evento.alcance
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
        if hasattr(evento, "revertida_en"):
            base["revertida_en"] = (
                evento.revertida_en.isoformat() if evento.revertida_en else None
            )
        if hasattr(evento, "nuevo_alcance") and evento.nuevo_alcance:
            base["nuevo_alcance"] = dataclasses.asdict(evento.nuevo_alcance)
        if hasattr(evento, "razon"):
            base["razon"] = evento.razon

        # ── Campos de eventos de integración ───────────────────────
        if hasattr(evento, "estado_anterior"):
            base["estado_anterior"] = evento.estado_anterior
        if hasattr(evento, "estado_nuevo"):
            base["estado_nuevo"] = evento.estado_nuevo
        if hasattr(evento, "actualizado_en"):
            base["actualizado_en"] = (
                evento.actualizado_en.isoformat() if evento.actualizado_en else None
            )
        if hasattr(evento, "asignado_en"):
            base["asignado_en"] = (
                evento.asignado_en.isoformat() if evento.asignado_en else None
            )
        if hasattr(evento, "detalles_trabajo"):
            base["detalles_trabajo"] = evento.detalles_trabajo

        return base
