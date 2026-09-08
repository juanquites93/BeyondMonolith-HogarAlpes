from __future__ import annotations
import uuid
from abc import ABC, abstractmethod
from typing import Optional

from marketplace_asignacion.domain.model import (
    Trabajo,
    EstadoInvalidoError,
    ProveedorNoAcreditadoError,
)
from marketplace_asignacion.domain.repository import TrabajoRepository


class AcreditacionPort(ABC):
    """Puerto para verificar acreditación de proveedores (anti-corruption layer)."""

    @abstractmethod
    def esta_acreditado(self, proveedor_id: uuid.UUID) -> bool:
        raise NotImplementedError


class AsignacionService:
    def __init__(
        self,
        trabajo_repo: TrabajoRepository,
        acreditacion: AcreditacionPort,
    ):
        self._repo = trabajo_repo
        self._acreditacion = acreditacion

    def seleccionar_proveedor_para_trabajo(
        self,
        trabajo_id: uuid.UUID,
        proveedor_id: uuid.UUID,
        correlation_id: Optional[str] = None,
    ) -> Trabajo:
        trabajo = self._repo.get(trabajo_id)
        if trabajo is None:
            raise ValueError(f"Trabajo {trabajo_id} no encontrado")

        acreditado = self._acreditacion.esta_acreditado(proveedor_id)
        trabajo.seleccionar_proveedor(
            proveedor_id=proveedor_id,
            acreditado=acreditado,
            correlation_id=correlation_id,
        )
        self._repo.update(trabajo)
        return trabajo
