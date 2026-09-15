"""Servicios de dominio."""

from __future__ import annotations
import uuid
from typing import Optional

from verificacion_acreditacion.domain.model import Proveedor
from verificacion_acreditacion.domain.repository import ProveedorRepository


class VerificacionService:
    def __init__(self, repo: ProveedorRepository):
        self._repo = repo

    def iniciar_verificacion(
        self, proveedor_id: uuid.UUID, correlation_id: Optional[str] = None
    ) -> Proveedor:
        proveedor = self._repo.get(proveedor_id)
        if proveedor is None:
            proveedor = Proveedor(id=proveedor_id)
            self._repo.add(proveedor)
        proveedor.iniciar_verificacion(correlation_id=correlation_id)
        self._repo.update(proveedor)
        return proveedor

    def aprobar_verificacion(
        self, proveedor_id: uuid.UUID, correlation_id: Optional[str] = None
    ) -> Proveedor:
        proveedor = self._repo.get(proveedor_id)
        if proveedor is None:
            raise ValueError(f"Proveedor {proveedor_id} no encontrado")
        proveedor.aprobar_verificacion(correlation_id=correlation_id)
        self._repo.update(proveedor)
        return proveedor

    def rechazar_verificacion(
        self,
        proveedor_id: uuid.UUID,
        motivo: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Proveedor:
        proveedor = self._repo.get(proveedor_id)
        if proveedor is None:
            raise ValueError(f"Proveedor {proveedor_id} no encontrado")
        proveedor.rechazar_verificacion(motivo=motivo, correlation_id=correlation_id)
        self._repo.update(proveedor)
        return proveedor

    def acreditar_proveedor(
        self, proveedor_id: uuid.UUID, correlation_id: Optional[str] = None
    ) -> Proveedor:
        proveedor = self._repo.get(proveedor_id)
        if proveedor is None:
            raise ValueError(f"Proveedor {proveedor_id} no encontrado")
        proveedor.acreditar(correlation_id=correlation_id)
        self._repo.update(proveedor)
        return proveedor
