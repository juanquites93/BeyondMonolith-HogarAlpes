import uuid
import pytest
from fastapi.testclient import TestClient

from marketplace_asignacion.infrastructure import database as db_module
from marketplace_asignacion.infrastructure.orm import OutboxORM, TrabajoORM


@pytest.fixture
def client(test_db):
    from marketplace_asignacion.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def acreditar_proveedor():
    from marketplace_asignacion.interfaces.api import _acreditacion_adapter

    def _fn(pid: uuid.UUID):
        _acreditacion_adapter.acreditar(pid)

    return _fn


def test_solicitar_trabajo_persiste_y_genera_outbox(client):
    payload = {
        "cliente_id": str(uuid.uuid4()),
        "ubicacion": {"direccion": "Calle 1", "ciudad": "Bogotá", "pais": "CO"},
        "alcance": {"descripcion": "Pintura", "categoria": "Pintura"},
    }
    resp = client.post("/trabajos/solicitar", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["estado"] == "SOLICITADO"
    trabajo_id = data["trabajo_id"]

    db = db_module.SessionLocal()
    orm = db.get(TrabajoORM, trabajo_id)
    assert orm is not None
    assert orm.estado == "SOLICITADO"
    outbox = db.query(OutboxORM).filter_by(aggregate_id=trabajo_id).all()
    assert any(o.event_type == "TrabajoSolicitado" for o in outbox)
    db.close()


def test_publicar_trabajo_transiciona_estado_y_genera_eventos_integracion(client):
    payload = {
        "cliente_id": str(uuid.uuid4()),
        "ubicacion": {"direccion": "Calle 1", "ciudad": "Bogotá", "pais": "CO"},
        "alcance": {"descripcion": "Pintura", "categoria": "Pintura"},
    }
    r1 = client.post("/trabajos/solicitar", json=payload)
    tid = r1.json()["trabajo_id"]

    r2 = client.post(f"/trabajos/{tid}/publicar", json={})
    assert r2.status_code == 200
    assert r2.json()["estado"] == "PUBLICADO"

    db = db_module.SessionLocal()
    outbox = db.query(OutboxORM).filter_by(aggregate_id=tid).all()

    # Evento de dominio
    assert any(o.event_type == "TrabajoPublicado" for o in outbox)
    # Eventos de integración
    assert any(o.event_type == "GenerarCotizacionCommand" for o in outbox)
    cotizacion = [o for o in outbox if o.event_type == "GenerarCotizacionCommand"][0]
    assert cotizacion.payload["trabajo_id"] == tid
    assert cotizacion.payload["ubicacion"]["ciudad"] == "Bogotá"
    assert cotizacion.payload["alcance"]["categoria"] == "Pintura"

    assert any(o.event_type == "TrabajoActualizado" for o in outbox)
    actualizado = [o for o in outbox if o.event_type == "TrabajoActualizado"][0]
    assert actualizado.payload["estado_anterior"] == "SOLICITADO"
    assert actualizado.payload["estado_nuevo"] == "PUBLICADO"
    db.close()


def test_seleccionar_proveedor_valida_acreditacion(client, acreditar_proveedor):
    payload = {
        "cliente_id": str(uuid.uuid4()),
        "ubicacion": {"direccion": "Calle 1", "ciudad": "Bogotá", "pais": "CO"},
        "alcance": {"descripcion": "Pintura", "categoria": "Pintura"},
    }
    r1 = client.post("/trabajos/solicitar", json=payload)
    tid = r1.json()["trabajo_id"]
    client.post(f"/trabajos/{tid}/publicar", json={})

    proveedor_id = uuid.uuid4()
    # Sin acreditar -> debe fallar con 409 (conflict) por regla de negocio
    r3 = client.post(
        f"/trabajos/{tid}/seleccionar-proveedor",
        json={"proveedor_id": str(proveedor_id)},
    )
    assert r3.status_code == 409

    # Acreditar y reintentar
    acreditar_proveedor(proveedor_id)
    r4 = client.post(
        f"/trabajos/{tid}/seleccionar-proveedor",
        json={"proveedor_id": str(proveedor_id)},
    )
    assert r4.status_code == 200
    assert r4.json()["estado"] == "PROVEEDOR_SELECCIONADO"
    assert r4.json()["proveedor_seleccionado_id"] == str(proveedor_id)


def test_seleccionar_proveedor_genera_eventos_integracion(client, acreditar_proveedor):
    payload = {
        "cliente_id": str(uuid.uuid4()),
        "ubicacion": {"direccion": "Calle 1", "ciudad": "Bogotá", "pais": "CO"},
        "alcance": {"descripcion": "Pintura", "categoria": "Pintura"},
    }
    r1 = client.post("/trabajos/solicitar", json=payload)
    tid = r1.json()["trabajo_id"]
    client.post(f"/trabajos/{tid}/publicar", json={})

    proveedor_id = uuid.uuid4()
    acreditar_proveedor(proveedor_id)
    r4 = client.post(
        f"/trabajos/{tid}/seleccionar-proveedor",
        json={"proveedor_id": str(proveedor_id)},
    )
    assert r4.status_code == 200

    db = db_module.SessionLocal()
    # ProveedorSeleccionadoParaValidacion tiene aggregate_id=proveedor_id, no tid
    outbox = db.query(OutboxORM).all()

    # Verificación
    assert any(
        o.event_type == "ProveedorSeleccionadoParaValidacion"
        and o.payload.get("trabajo_id") == str(tid)
        for o in outbox
    )

    # Broadcast
    assert any(
        o.event_type == "ProveedorAsignadoAlTrabajo"
        and o.payload.get("trabajo_id") == str(tid)
        for o in outbox
    )

    # Notificaciones
    assert any(
        o.event_type == "NotificarProveedorAsignadoCommand"
        and o.payload.get("trabajo_id") == str(tid)
        for o in outbox
    )
    notif_prov = [
        o
        for o in outbox
        if o.event_type == "NotificarProveedorAsignadoCommand"
        and o.payload.get("trabajo_id") == str(tid)
    ][0]
    assert notif_prov.payload["proveedor_id"] == str(proveedor_id)
    assert notif_prov.payload["detalles_trabajo"]["categoria"] == "Pintura"

    assert any(
        o.event_type == "NotificarClienteProveedorAsignadoCommand"
        and o.payload.get("trabajo_id") == str(tid)
        for o in outbox
    )
    notif_cli = [
        o
        for o in outbox
        if o.event_type == "NotificarClienteProveedorAsignadoCommand"
        and o.payload.get("trabajo_id") == str(tid)
    ][0]
    assert notif_cli.payload["cliente_id"] == r1.json()["cliente_id"]

    db.close()


def test_idempotencia_solicitar_trabajo(client):
    payload = {
        "cliente_id": str(uuid.uuid4()),
        "ubicacion": {"direccion": "Calle 1", "ciudad": "Bogotá", "pais": "CO"},
        "alcance": {"descripcion": "Pintura", "categoria": "Pintura"},
        "idempotency_key": "idem-001",
    }
    r1 = client.post("/trabajos/solicitar", json=payload)
    assert r1.status_code == 201
    tid1 = r1.json()["trabajo_id"]

    r2 = client.post("/trabajos/solicitar", json=payload)
    assert r2.status_code == 200  # segunda vez devuelve cached
    # Al ser idempotente, debe retornar el mismo resultado serializado
    assert r2.json()["trabajo_id"] == tid1
    assert r2.json()["estado"] == "SOLICITADO"
