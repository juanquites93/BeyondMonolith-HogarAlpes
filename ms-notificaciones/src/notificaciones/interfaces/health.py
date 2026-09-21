from fastapi import APIRouter, Response
from sqlalchemy import text

from notificaciones.infrastructure.database import engine
from notificaciones.infrastructure.pulsar_consumidor import consumidor_esta_listo

router = APIRouter()


@router.get("/health")
def health_check():
    """Liveness: solo responde si el proceso sigue vivo. No revisa
    dependencias externas (BD, Pulsar) — para eso esta /ready."""
    return {"status": "ok", "service": "ms-notificaciones"}


@router.get("/ready")
def readiness_check(response: Response):
    """Readiness: True solo si el servicio puede atender trafico de verdad.

    Revisa la base de datos siempre, y el consumidor de Pulsar solo cuando
    PULSAR_SERVICE_URL esta configurado (igual criterio que el resto del
    servicio). Responde 503 si algo falla, para que un balanceador de carga
    deje de enviarle trafico a esta replica.
    """
    checks: dict[str, str] = {}
    healthy = True

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        healthy = False

    if consumidor_esta_listo():
        checks["pulsar"] = "ok"
    else:
        checks["pulsar"] = "error: consumidor no conectado"
        healthy = False

    response.status_code = 200 if healthy else 503
    return {"status": "ok" if healthy else "error", "checks": checks}
