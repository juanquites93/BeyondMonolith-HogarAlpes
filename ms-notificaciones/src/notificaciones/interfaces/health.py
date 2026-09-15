from fastapi import APIRouter
from sqlalchemy import text

from notificaciones.infrastructure.database import engine

router = APIRouter()


@router.get("/health")
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "service": "ms-notificaciones"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
