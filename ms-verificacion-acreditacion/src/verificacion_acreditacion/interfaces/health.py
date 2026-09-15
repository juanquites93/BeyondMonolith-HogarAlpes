"""Health checks."""

from fastapi import APIRouter
from sqlalchemy import text

from verificacion_acreditacion.infrastructure.database import engine

router = APIRouter()


@router.get("/health")
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "service": "verificacion-acreditacion"}
    except Exception as e:
        return {
            "status": "error",
            "service": "verificacion-acreditacion",
            "detail": str(e),
        }
