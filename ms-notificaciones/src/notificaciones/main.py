import logging
import sys
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from notificaciones.infrastructure import database as db_module
from notificaciones.infrastructure.config import settings
from notificaciones.infrastructure.pulsar_consumidor import iniciar_consumidor_en_hilo
from notificaciones.domain.model import EstadoInvalidoError
from notificaciones.interfaces.api import router as api_router
from notificaciones.interfaces.health import router as health_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Microservicio Notificaciones - Hogar de los Alpes",
)

app.include_router(health_router)
app.include_router(api_router)


@app.exception_handler(EstadoInvalidoError)
def estado_invalido_handler(request: Request, exc: EstadoInvalidoError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.on_event("startup")
def on_startup():
    db_module.Base.metadata.create_all(bind=db_module.engine)
    iniciar_consumidor_en_hilo()
