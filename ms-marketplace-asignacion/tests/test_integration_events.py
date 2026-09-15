"""Tests de mapping y contrato de eventos de integración."""

import uuid
from datetime import datetime

from marketplace_asignacion.application.integration_events import (
    GenerarCotizacionCommand,
    ProveedorAsignadoAlTrabajo,
    NotificarProveedorAsignadoCommand,
    NotificarClienteProveedorAsignadoCommand,
    TrabajoActualizado,
)


def test_generar_cotizacion_command_payload():
    cmd = GenerarCotizacionCommand(
        correlation_id="corr-123",
        aggregate_id=uuid.uuid4(),
        trabajo_id=uuid.uuid4(),
        cliente_id=uuid.uuid4(),
        ubicacion={"direccion": "Calle 1", "ciudad": "Bogotá", "pais": "CO"},
        alcance={"descripcion": "Pintura", "categoria": "Pintura"},
    )
    assert cmd.event_type == "GenerarCotizacionCommand"
    assert cmd.version == 1
    assert cmd.correlation_id == "corr-123"
    assert cmd.ubicacion["ciudad"] == "Bogotá"
    assert cmd.alcance["categoria"] == "Pintura"


def test_proveedor_asignado_al_trabajo_payload():
    evt = ProveedorAsignadoAlTrabajo(
        correlation_id="corr-456",
        aggregate_id=uuid.uuid4(),
        trabajo_id=uuid.uuid4(),
        proveedor_id=uuid.uuid4(),
        cliente_id=uuid.uuid4(),
    )
    assert evt.event_type == "ProveedorAsignadoAlTrabajo"
    assert evt.asignado_en is not None


def test_notificar_proveedor_asignado_command_payload():
    cmd = NotificarProveedorAsignadoCommand(
        correlation_id="corr-789",
        aggregate_id=uuid.uuid4(),
        proveedor_id=uuid.uuid4(),
        trabajo_id=uuid.uuid4(),
        cliente_id=uuid.uuid4(),
        detalles_trabajo={"descripcion": "Pintura", "categoria": "Pintura"},
    )
    assert cmd.event_type == "NotificarProveedorAsignadoCommand"
    assert cmd.detalles_trabajo["categoria"] == "Pintura"


def test_notificar_cliente_proveedor_asignado_command_payload():
    cmd = NotificarClienteProveedorAsignadoCommand(
        correlation_id="corr-abc",
        aggregate_id=uuid.uuid4(),
        cliente_id=uuid.uuid4(),
        trabajo_id=uuid.uuid4(),
        proveedor_id=uuid.uuid4(),
    )
    assert cmd.event_type == "NotificarClienteProveedorAsignadoCommand"
    assert cmd.cliente_id is not None


def test_trabajo_actualizado_payload():
    evt = TrabajoActualizado(
        correlation_id="corr-def",
        aggregate_id=uuid.uuid4(),
        trabajo_id=uuid.uuid4(),
        cliente_id=uuid.uuid4(),
        estado_anterior="SOLICITADO",
        estado_nuevo="PUBLICADO",
    )
    assert evt.event_type == "TrabajoActualizado"
    assert evt.estado_anterior == "SOLICITADO"
    assert evt.estado_nuevo == "PUBLICADO"
    assert evt.actualizado_en is not None
