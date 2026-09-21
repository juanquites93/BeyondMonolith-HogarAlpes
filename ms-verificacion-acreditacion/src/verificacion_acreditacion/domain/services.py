"""Servicios de dominio."""

from __future__ import annotations
import uuid
from typing import Optional

from verificacion_acreditacion.domain.model import Proveedor
from verificacion_acreditacion.domain.repository import ProveedorRepository
from verificacion_acreditacion.domain.value_objects import (
    EstadoAcreditacion,
    EstadoVerificacion,
)
from verificacion_acreditacion.application.external_validation_port import (
    ExternalValidationPort,
    ExternalValidationError,
)


class VerificacionService:
    def __init__(
        self,
        repo: ProveedorRepository,
        external_validation: ExternalValidationPort,
    ):
        self._repo = repo
        self._external_validation = external_validation

    def iniciar_verificacion(
        self,
        proveedor_id: uuid.UUID,
        trabajo_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Proveedor:
        proveedor = self._repo.get(proveedor_id)
        if proveedor is None:
            proveedor = Proveedor(id=proveedor_id)
            self._repo.add(proveedor)

        # Idempotencia: si el proveedor ya fue acreditado, regeneramos el evento
        # para que el outbox worker lo publique nuevamente y la saga avance.
        if proveedor.estado_acreditacion == EstadoAcreditacion.ACREDITADO:
            proveedor.acreditar(correlation_id=correlation_id)
            self._repo.update(proveedor)
            return proveedor

        # Si la verificación ya fue aprobada pero la acreditación fue revocada
        # (por compensación), simplemente acreditamos de nuevo.
        if proveedor.estado_verificacion == EstadoVerificacion.APROBADA:
            proveedor.acreditar(correlation_id=correlation_id)
            self._repo.update(proveedor)
            return proveedor

        # Si la verificación fue rechazada, no se puede continuar.
        if proveedor.estado_verificacion == EstadoVerificacion.RECHAZADA:
            raise ValueError(f"Proveedor {proveedor_id} fue rechazado previamente")

        try:
            self._external_validation.validar(proveedor_id)
        except ExternalValidationError as exc:
            proveedor.marcar_verificacion_pendiente(
                trabajo_id=trabajo_id,
                motivo=str(exc),
                correlation_id=correlation_id,
            )
            self._repo.update(proveedor)
            return proveedor

        proveedor.iniciar_verificacion(
            trabajo_id=trabajo_id, correlation_id=correlation_id
        )
        proveedor.aprobar_verificacion(correlation_id=correlation_id)
        proveedor.acreditar(correlation_id=correlation_id)
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

    def revocar_acreditacion(
        self,
        proveedor_id: uuid.UUID,
        acreditacion_id: Optional[uuid.UUID] = None,
        correlation_id: Optional[str] = None,
    ) -> Proveedor:
        proveedor = self._repo.get(proveedor_id)
        if proveedor is None:
            raise ValueError(f"Proveedor {proveedor_id} no encontrado")
        proveedor.revocar_acreditacion(
            acreditacion_id=acreditacion_id, correlation_id=correlation_id
        )
        self._repo.update(proveedor)
        return proveedor
