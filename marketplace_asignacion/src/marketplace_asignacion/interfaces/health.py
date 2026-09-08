from fastapi import APIRouter
from sqlalchemy import text

from marketplace_asignacion.infrastructure.database import engine

router = APIRouter()


@router.get("/health")
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "service": "marketplace-asignacion"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
