"""Tests de dominio: invariantes."""

import uuid
import pytest

from verificacion_acreditacion.domain.model import Proveedor
from verificacion_acreditacion.domain.value_objects import (
    EstadoVerificacion,
    EstadoAcreditacion,
)
from verificacion_acreditacion.domain.exceptions import (
    ProveedorNoVerificadoError,
    VerificacionYaResueltaError,
)


def test_iniciar_verificacion_crea_evento():
    p = Proveedor()
    p.iniciar_verificacion()
    assert p.estado_verificacion == EstadoVerificacion.PENDIENTE
    assert any(e.event_type == "VerificacionProveedorIniciada" for e in p.eventos)


def test_aprobar_verificacion_cambia_estado():
    p = Proveedor()
    p.iniciar_verificacion()
    p.aprobar_verificacion()
    assert p.estado_verificacion == EstadoVerificacion.APROBADA


def test_rechazar_verificacion_cambia_estado():
    p = Proveedor()
    p.iniciar_verificacion()
    p.rechazar_verificacion(motivo="Documento inválido")
    assert p.estado_verificacion == EstadoVerificacion.RECHAZADA


def test_no_se_puede_acreditar_sin_verificacion_aprobada():
    p = Proveedor()
    with pytest.raises(ProveedorNoVerificadoError):
        p.acreditar()


def test_acreditar_despues_de_aprobar():
    p = Proveedor()
    p.iniciar_verificacion()
    p.aprobar_verificacion()
    p.acreditar()
    assert p.estado_acreditacion == EstadoAcreditacion.ACREDITADO


def test_no_aprobar_dos_veces():
    p = Proveedor()
    p.iniciar_verificacion()
    p.aprobar_verificacion()
    with pytest.raises(VerificacionYaResueltaError):
        p.aprobar_verificacion()


def test_no_rechazar_dos_veces():
    p = Proveedor()
    p.iniciar_verificacion()
    p.rechazar_verificacion()
    with pytest.raises(VerificacionYaResueltaError):
        p.rechazar_verificacion()
