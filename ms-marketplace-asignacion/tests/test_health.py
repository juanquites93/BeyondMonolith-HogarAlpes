"""Smoke test: health check."""

from fastapi.testclient import TestClient

from marketplace_asignacion.main import app


def test_health_check():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    # El health check responde 200 aunque la DB esté caída,
    # pero marca status=error en el payload
    assert data["service"] == "marketplace-asignacion"
    assert data["status"] in ("ok", "error")
