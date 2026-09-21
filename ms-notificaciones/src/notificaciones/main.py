import logging
import sys
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from notificaciones.infrastructure import database as db_module
from notificaciones.infrastructure.config import settings
from notificaciones.infrastructure.pulsar_consumidor import iniciar_consumidor_en_hilo
from notificaciones.domain.model import EstadoInvalidoError
from notificaciones.interfaces.api import router as api_router
from notificaciones.interfaces.health import router as health_router


class _InstanceIdLogFilter(logging.Filter):
    """Agrega el instance_id de esta replica a cada linea de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.instance_id = settings.INSTANCE_ID
        return True


_log_handler = logging.StreamHandler(sys.stdout)
_log_handler.addFilter(_InstanceIdLogFilter())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s [instance=%(instance_id)s] %(message)s",
    handlers=[_log_handler],
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Microservicio Notificaciones - Hogar de los Alpes",
)

app.include_router(health_router)
app.include_router(api_router)

# Expone /metrics con requests OK/fallidos y latencia por endpoint. Los
# contadores propios de eventos (consumo de Pulsar) estan en
# infrastructure/metrics.py y se registran en el mismo endpoint.
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.middleware("http")
async def agregar_header_instance_id(request: Request, call_next):
    """Deja explicito, en cada respuesta, que replica la atendio."""
    response = await call_next(request)
    response.headers["X-Instance-Id"] = settings.INSTANCE_ID
    return response


@app.exception_handler(EstadoInvalidoError)
def estado_invalido_handler(request: Request, exc: EstadoInvalidoError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.on_event("startup")
def on_startup():
    db_module.Base.metadata.create_all(bind=db_module.engine)
    iniciar_consumidor_en_hilo()
