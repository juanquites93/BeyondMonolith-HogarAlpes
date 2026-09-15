import logging
import sys
import threading
import time

from fastapi import FastAPI

from generador_cotizacion.infrastructure import database as db_module
from generador_cotizacion.infrastructure.config import settings
from generador_cotizacion.interfaces.api import router as api_router
from generador_cotizacion.interfaces.health import router as health_router
from generador_cotizacion.interfaces.messaging.consumer import (
    handle_incoming_message,
)
from generador_cotizacion.infrastructure.pulsar_consumer import (
    PulsarCommandConsumer,
)
from generador_cotizacion.infrastructure.pulsar_producer import PulsarEventProducer

# Logging estructurado básico
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Microservicio Generador de Cotización - Hogar de los Alpes",
)

app.include_router(health_router)
app.include_router(api_router)


def _start_consumer_with_retry(max_retries: int = 10, delay: int = 5) -> None:
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
                f"Error iniciando consumer Pulsar (intento {attempt}): {exc}",
                exc_info=True,
            )
            if attempt < max_retries:
                logger.info(f"Reintentando en {delay} segundos...")
                time.sleep(delay)
            else:
                logger.error("Agotados todos los reintentos del consumer Pulsar")


def _start_outbox_relay(interval_seconds: int = 3) -> None:
    """Publica periódicamente los eventos pendientes del outbox hacia Pulsar."""
    producer = PulsarEventProducer(db_module.SessionLocal)
    while True:
        try:
            producer.publish_pending()
        except Exception as exc:
            logger.warning(f"Error publicando outbox a Pulsar: {exc}")
        time.sleep(interval_seconds)


@app.on_event("startup")
def on_startup():
    db_module.Base.metadata.create_all(bind=db_module.engine)

    logger.info("Iniciando consumer Pulsar en background thread")
    threading.Thread(target=_start_consumer_with_retry, daemon=True).start()

    logger.info("Iniciando relay de outbox hacia Pulsar en background thread")
    threading.Thread(target=_start_outbox_relay, daemon=True).start()
