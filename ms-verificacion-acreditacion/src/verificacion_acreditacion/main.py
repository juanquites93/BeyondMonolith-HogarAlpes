"""Punto de entrada FastAPI."""

import logging
import sys
import threading
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from verificacion_acreditacion.infrastructure import database as db_module
from verificacion_acreditacion.infrastructure.config import settings
from verificacion_acreditacion.domain.exceptions import VerificacionError
from verificacion_acreditacion.interfaces.api.router import router as api_router
from verificacion_acreditacion.interfaces.health import router as health_router
from verificacion_acreditacion.interfaces.messaging.consumer import (
    handle_incoming_message,
)
from verificacion_acreditacion.infrastructure.pulsar_consumer import (
    PulsarCommandConsumer,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Microservicio Verificación y Acreditación - Hogar de los Alpes",
)

app.include_router(health_router)
app.include_router(api_router)


@app.exception_handler(VerificacionError)
def verificacion_error_handler(request: Request, exc: VerificacionError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


def _start_consumer_with_retry(max_retries=10, delay=5):
    """Inicia el consumer de Pulsar con reintentos."""
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"Intentando iniciar consumer Pulsar (intento {attempt}/{max_retries})"
            )
            consumer = PulsarCommandConsumer(handler=handle_incoming_message)
            consumer.start()
        except Exception as exc:
            logger.error(
                f"Error iniciando consumer Pulsar (intento {attempt}): {str(exc)}",
                exc_info=True,
            )
            if attempt < max_retries:
                logger.info(f"Reintentando en {delay} segundos...")
                time.sleep(delay)
            else:
                logger.error("Agotados todos los reintentos del consumer Pulsar")


@app.on_event("startup")
def on_startup():
    db_module.Base.metadata.create_all(bind=db_module.engine)

    # Iniciar consumer de Pulsar en background thread con retry
    logger.info("Iniciando consumer Pulsar en background thread")
    thread = threading.Thread(target=_start_consumer_with_retry, daemon=True)
    thread.start()
