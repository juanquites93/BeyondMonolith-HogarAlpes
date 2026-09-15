import uuid
import pytest
from datetime import datetime

from marketplace_asignacion.domain.model import Trabajo
from marketplace_asignacion.domain.value_objects import Ubicacion, Alcance
from marketplace_asignacion.domain.events import (
    TrabajoSolicitado,
    TrabajoPublicado,
    ProveedorSeleccionado,
)


def _assert_base_event_fields(evento):
    assert evento.event_id is not None
    assert evento.event_type == evento.__class__.__name__
    assert evento.version == 1
    assert isinstance(evento.occurred_at, datetime)
    assert evento.aggregate_id is not None


def test_evento_trabajo_solicitado_payload():
    trabajo = Trabajo(
        cliente_id=uuid.uuid4(),
        ubicacion=Ubicacion(direccion="Av Reforma", ciudad="CDMX", pais="MX"),
        alcance=Alcance(descripcion="Instalación eléctrica", categoria="Electricidad"),
    )
    trabajo.solicitar(correlation_id="corr-123")
    evento = trabajo.eventos[0]
    _assert_base_event_fields(evento)
    assert evento.correlation_id == "corr-123"
    assert evento.trabajo_id == trabajo.id
    assert evento.cliente_id == trabajo.cliente_id
    assert evento.ubicacion.direccion == "Av Reforma"
    assert evento.alcance.categoria == "Electricidad"


def test_evento_trabajo_publicado_payload():
    trabajo = Trabajo(
        cliente_id=uuid.uuid4(),
        ubicacion=Ubicacion(direccion="Av Reforma", ciudad="CDMX", pais="MX"),
        alcance=Alcance(descripcion="Instalación eléctrica", categoria="Electricidad"),
    )
    trabajo.solicitar()
    trabajo.publicar(correlation_id="corr-456")
    evento = [e for e in trabajo.eventos if isinstance(e, TrabajoPublicado)][0]
    _assert_base_event_fields(evento)
    assert evento.correlation_id == "corr-456"
    assert evento.trabajo_id == trabajo.id
    assert evento.cliente_id == trabajo.cliente_id
    assert evento.publicado_en is not None


def test_evento_proveedor_seleccionado_payload():
    trabajo = Trabajo(
        cliente_id=uuid.uuid4(),
        ubicacion=Ubicacion(direccion="Av Reforma", ciudad="CDMX", pais="MX"),
        alcance=Alcance(descripcion="Instalación eléctrica", categoria="Electricidad"),
    )
    trabajo.solicitar()
    trabajo.publicar()
    pid = uuid.uuid4()
    trabajo.seleccionar_proveedor(
        proveedor_id=pid, acreditado=True, correlation_id="corr-789"
    )
    evento = [e for e in trabajo.eventos if isinstance(e, ProveedorSeleccionado)][0]
    _assert_base_event_fields(evento)
    assert evento.correlation_id == "corr-789"
    assert evento.trabajo_id == trabajo.id
    assert evento.proveedor_id == pid
    assert evento.seleccionado_en is not None
