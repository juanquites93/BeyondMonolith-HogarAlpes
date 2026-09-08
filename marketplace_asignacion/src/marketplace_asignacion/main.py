import logging
import sys
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from marketplace_asignacion.infrastructure import database as db_module
from marketplace_asignacion.infrastructure.config import settings
from marketplace_asignacion.domain.model import (
    EstadoInvalidoError,
    ProveedorNoAcreditadoError,
)
from marketplace_asignacion.interfaces.api import router as api_router
from marketplace_asignacion.interfaces.health import router as health_router

# Logging estructurado básico
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Microservicio Marketplace y Asignación - Hogar de los Alpes",
)

app.include_router(health_router)
app.include_router(api_router)


@app.exception_handler(EstadoInvalidoError)
def estado_invalido_handler(request: Request, exc: EstadoInvalidoError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ProveedorNoAcreditadoError)
def proveedor_no_acreditado_handler(request: Request, exc: ProveedorNoAcreditadoError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.on_event("startup")
def on_startup():
    db_module.Base.metadata.create_all(bind=db_module.engine)
