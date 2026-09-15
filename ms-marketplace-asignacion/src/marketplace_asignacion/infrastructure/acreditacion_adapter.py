from __future__ import annotations
import uuid

from marketplace_asignacion.domain.services import AcreditacionPort


class FakeAcreditacionAdapter(AcreditacionPort):
    """Adaptador simulado de acreditación.

    En producción consultaría el microservicio de Proveedores
    o una caché distribuida (Redis) con TTL.
    """

    def __init__(self, acreditados: set[uuid.UUID] | None = None):
        self._acreditados = acreditados or set()

    def esta_acreditado(self, proveedor_id: uuid.UUID) -> bool:
        return proveedor_id in self._acreditados

    def acreditar(self, proveedor_id: uuid.UUID) -> None:
        self._acreditados.add(proveedor_id)
