from __future__ import annotations
import uuid
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, field

from generador_cotizacion.domain.events import (
    DomainEvent,
    CotizacionSolicitada,
    CotizacionCancelada,
)
from generador_cotizacion.domain.value_objects import EstadoCotizacion


@dataclass
class Cotizacion:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    trabajo_id: uuid.UUID = None
    proveedor_id: Optional[uuid.UUID] = None
    monto: Optional[float] = None
    moneda: str = "COP"
    descripcion: str = ""
    estado: EstadoCotizacion = EstadoCotizacion.SOLICITADA
    fecha_solicitud: datetime = field(default_factory=datetime.utcnow)
    fecha_validez: Optional[datetime] = None
    _eventos: List[DomainEvent] = field(default_factory=list, repr=False)

    @property
    def eventos(self) -> List[DomainEvent]:
        return list(self._eventos)

    def limpiar_eventos(self) -> None:
        self._eventos.clear()

    def _aplicar_evento(self, evento: DomainEvent) -> None:
        evento.aggregate_id = self.id
        self._eventos.append(evento)

    @classmethod
    def solicitar(
        cls,
        trabajo_id: uuid.UUID,
        descripcion: str,
        proveedor_id: Optional[uuid.UUID] = None,
        monto: Optional[float] = None,
        moneda: str = "COP",
        fecha_validez: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
    ) -> "Cotizacion":
        cotizacion = cls(
            trabajo_id=trabajo_id,
            proveedor_id=proveedor_id,
            monto=monto,
            moneda=moneda,
            descripcion=descripcion,
            fecha_validez=fecha_validez,
        )
        evento = CotizacionSolicitada(
            cotizacion_id=cotizacion.id,
            trabajo_id=trabajo_id,
            proveedor_id=proveedor_id,
            monto=monto,
            moneda=moneda,
            descripcion=descripcion,
            correlation_id=correlation_id,
        )
        cotizacion._aplicar_evento(evento)
        return cotizacion

    def cancelar(self, correlation_id: Optional[str] = None) -> None:
        if self.estado == EstadoCotizacion.CANCELADA:
            return
        self.estado = EstadoCotizacion.CANCELADA
        evento = CotizacionCancelada(
            cotizacion_id=self.id,
            trabajo_id=self.trabajo_id,
            proveedor_id=self.proveedor_id,
            correlation_id=correlation_id,
        )
        self._aplicar_evento(evento)
