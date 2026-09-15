import uuid
import pytest

from marketplace_asignacion.domain.model import (
    Trabajo,
    EstadoInvalidoError,
    ProveedorNoAcreditadoError,
)
from marketplace_asignacion.domain.value_objects import (
    Ubicacion,
    Alcance,
    EstadoTrabajo,
)
from marketplace_asignacion.domain.events import (
    TrabajoSolicitado,
    TrabajoPublicado,
    ProveedorSeleccionado,
)


def test_solicitar_trabajo_genera_evento_y_cambia_estado():
    trabajo = Trabajo(
        cliente_id=uuid.uuid4(),
        ubicacion=Ubicacion(direccion="Calle 123", ciudad="Bogotá", pais="CO"),
        alcance=Alcance(descripcion="Reparación de tubería", categoria="Plomería"),
    )
    trabajo.solicitar()
    assert trabajo.estado == EstadoTrabajo.SOLICITADO
    assert len(trabajo.eventos) == 1
    assert isinstance(trabajo.eventos[0], TrabajoSolicitado)
    assert trabajo.eventos[0].trabajo_id == trabajo.id


def test_publicar_sin_solicitar_falla():
    trabajo = Trabajo(
        cliente_id=uuid.uuid4(),
        ubicacion=Ubicacion(direccion="Calle 123", ciudad="Bogotá", pais="CO"),
        alcance=Alcance(descripcion="Reparación", categoria="Plomería"),
    )
    with pytest.raises(EstadoInvalidoError):
        trabajo.publicar()


def test_publicar_tras_solicitar_cambia_estado():
    trabajo = Trabajo(
        cliente_id=uuid.uuid4(),
        ubicacion=Ubicacion(direccion="Calle 123", ciudad="Bogotá", pais="CO"),
        alcance=Alcance(descripcion="Reparación", categoria="Plomería"),
    )
    trabajo.solicitar()
    trabajo.limpiar_eventos()
    trabajo.publicar()
    assert trabajo.estado == EstadoTrabajo.PUBLICADO
    assert len(trabajo.eventos) == 1
    assert isinstance(trabajo.eventos[0], TrabajoPublicado)


def test_seleccionar_proveedor_sin_publicar_falla():
    trabajo = Trabajo(
        cliente_id=uuid.uuid4(),
        ubicacion=Ubicacion(direccion="Calle 123", ciudad="Bogotá", pais="CO"),
        alcance=Alcance(descripcion="Reparación", categoria="Plomería"),
    )
    trabajo.solicitar()
    with pytest.raises(EstadoInvalidoError):
        trabajo.seleccionar_proveedor(proveedor_id=uuid.uuid4(), acreditado=True)


def test_seleccionar_proveedor_no_acreditado_falla():
    trabajo = Trabajo(
        cliente_id=uuid.uuid4(),
        ubicacion=Ubicacion(direccion="Calle 123", ciudad="Bogotá", pais="CO"),
        alcance=Alcance(descripcion="Reparación", categoria="Plomería"),
    )
    trabajo.solicitar()
    trabajo.publicar()
    with pytest.raises(ProveedorNoAcreditadoError):
        trabajo.seleccionar_proveedor(proveedor_id=uuid.uuid4(), acreditado=False)


def test_seleccionar_proveedor_acreditado_exitoso():
    trabajo = Trabajo(
        cliente_id=uuid.uuid4(),
        ubicacion=Ubicacion(direccion="Calle 123", ciudad="Bogotá", pais="CO"),
        alcance=Alcance(descripcion="Reparación", categoria="Plomería"),
    )
    trabajo.solicitar()
    trabajo.publicar()
    proveedor_id = uuid.uuid4()
    trabajo.seleccionar_proveedor(proveedor_id=proveedor_id, acreditado=True)
    assert trabajo.estado == EstadoTrabajo.PROVEEDOR_SELECCIONADO
    assert trabajo.proveedor_seleccionado_id == proveedor_id
    evento = trabajo.eventos[-1]
    assert isinstance(evento, ProveedorSeleccionado)
    assert evento.proveedor_id == proveedor_id
