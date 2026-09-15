from __future__ import annotations
import uuid
from typing import List, Optional
from dataclasses import dataclass, field

from marketplace_asignacion.domain.events import (
    DomainEvent,
    TrabajoSolicitado,
    TrabajoPublicado,
    ProveedorSeleccionado,
    AlcanceCambiado,
)
from marketplace_asignacion.domain.value_objects import (
    Ubicacion,
    Alcance,
    EstadoTrabajo,
)


class EstadoInvalidoError(Exception):
    pass


class ProveedorNoAcreditadoError(Exception):
    pass


@dataclass
class Trabajo:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    cliente_id: uuid.UUID = None
    ubicacion: Optional[Ubicacion] = None
    alcance: Optional[Alcance] = None
    estado: EstadoTrabajo = EstadoTrabajo.BORRADOR
    proveedor_seleccionado_id: Optional[uuid.UUID] = None
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
        if self.estado != EstadoTrabajo.BORRADOR:
            raise EstadoInvalidoError(
                f"No se puede solicitar un trabajo en estado {self.estado.value}"
            )
        self.estado = EstadoTrabajo.SOLICITADO
        evento = TrabajoSolicitado(
            trabajo_id=self.id,
            cliente_id=self.cliente_id,
            ubicacion=self.ubicacion,
            alcance=self.alcance,
            correlation_id=correlation_id,
        )
        self._aplicar_evento(evento)

    def publicar(self, correlation_id: Optional[str] = None) -> None:
        if self.estado != EstadoTrabajo.SOLICITADO:
            raise EstadoInvalidoError(
                f"No se puede publicar un trabajo en estado {self.estado.value}"
            )
        self.estado = EstadoTrabajo.PUBLICADO
        evento = TrabajoPublicado(
            trabajo_id=self.id,
            cliente_id=self.cliente_id,
            correlation_id=correlation_id,
        )
        self._aplicar_evento(evento)

    def seleccionar_proveedor(
        self,
        proveedor_id: uuid.UUID,
        acreditado: bool,
        correlation_id: Optional[str] = None,
    ) -> None:
        if self.estado != EstadoTrabajo.PUBLICADO:
            raise EstadoInvalidoError(
                f"No se puede seleccionar proveedor en estado {self.estado.value}"
            )
        if not acreditado:
            raise ProveedorNoAcreditadoError(
                f"El proveedor {proveedor_id} no está acreditado"
            )
        self.proveedor_seleccionado_id = proveedor_id
        self.estado = EstadoTrabajo.PROVEEDOR_SELECCIONADO
        evento = ProveedorSeleccionado(
            trabajo_id=self.id,
            proveedor_id=proveedor_id,
            correlation_id=correlation_id,
        )
        self._aplicar_evento(evento)

    def cambiar_alcance(
        self,
        nuevo_alcance: Alcance,
        razon: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        self.alcance = nuevo_alcance
        evento = AlcanceCambiado(
            trabajo_id=self.id,
            nuevo_alcance=nuevo_alcance,
            razon=razon,
            correlation_id=correlation_id,
        )
        self._aplicar_evento(evento)
        # Extensión: podría revertir estado a SOLICITADO o PUBLICADO según reglas de negocio
