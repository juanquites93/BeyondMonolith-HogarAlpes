"""Aplicación FastAPI del orquestador de Sagas."""

import logging
import sys
import threading
import time

from fastapi import FastAPI

from ms_orquestador.infrastructure import database as db_module
from ms_orquestador.infrastructure.config import settings
from ms_orquestador.application.orchestrator import SagaOrchestrator
from ms_orquestador.infrastructure.pulsar_consumer import PulsarEventConsumer
from ms_orquestador.interfaces.api import router as api_router
from ms_orquestador.interfaces.health import router as health_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Orquestador de Sagas - Hogar de los Alpes",
)

app.include_router(health_router)
app.include_router(api_router)

_orchestrator: SagaOrchestrator | None = None


def _start_consumer_with_retry(max_retries: int = 10, delay: int = 5) -> None:
    global _orchestrator
    _orchestrator = SagaOrchestrator(session_factory=db_module.SessionLocal)

    consumer = PulsarEventConsumer(handler=_orchestrator.handle_event)
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "Intentando iniciar consumer Pulsar (intento %s/%s)",
                attempt,
                max_retries,
            )
            consumer.start()
            return
        except Exception as exc:
            logger.error(
                "Error iniciando consumer Pulsar (intento %s): %s",
                attempt,
                exc,
                exc_info=True,
            )
            if attempt < max_retries:
                logger.info("Reintentando en %s segundos...", delay)
                time.sleep(delay)
            else:
                logger.error("Agotados todos los reintentos del consumer Pulsar")


def _start_retry_worker(interval_seconds: int = 10) -> None:
    global _orchestrator
    while _orchestrator is None:
        time.sleep(1)
    while True:
        try:
            _orchestrator.process_retries()
        except Exception as exc:
            logger.warning("Error en retry worker: %s", exc)
        time.sleep(interval_seconds)


@app.on_event("startup")
def on_startup():
    db_module.Base.metadata.create_all(bind=db_module.engine)

    logger.info("Iniciando consumer Pulsar de la Saga en background")
    threading.Thread(target=_start_consumer_with_retry, daemon=True).start()

    logger.info("Iniciando retry worker de la Saga en background")
    threading.Thread(target=_start_retry_worker, daemon=True).start()
