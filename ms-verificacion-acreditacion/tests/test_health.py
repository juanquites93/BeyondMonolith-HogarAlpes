"""Smoke test: health check."""

from fastapi.testclient import TestClient

from verificacion_acreditacion.main import app


def test_health_check():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "verificacion-acreditacion"
    assert data["status"] in ("ok", "error")
