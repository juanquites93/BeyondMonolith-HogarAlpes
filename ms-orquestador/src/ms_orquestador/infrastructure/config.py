"""Configuración del orquestador de Sagas."""

import os
from typing import Optional


class Settings:
    APP_NAME: str = "ms-orquestador"
    VERSION: str = "0.1.0"

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://hogar:alpes@localhost:5432/orquestador_db",
    )
    ECHO_SQL: bool = os.getenv("ECHO_SQL", "false").lower() == "true"
    IDEMPOTENCY_TTL_SECONDS: int = int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "86400"))

    # Pulsar
    PULSAR_SERVICE_URL: str = os.getenv("PULSAR_SERVICE_URL", "pulsar://localhost:6650")
    PULSAR_SUBSCRIPTION: str = os.getenv("PULSAR_SUBSCRIPTION", "orquestador-saga-sub")
    PULSAR_MAX_REDELIVER_COUNT: int = int(os.getenv("PULSAR_MAX_REDELIVER_COUNT", "5"))
    PULSAR_DLQ_TOPIC: str = os.getenv(
        "PULSAR_DLQ_TOPIC", "persistent://hogar/alpes/dlq"
    )

    # Tópicos de entrada (eventos que el orquestador consume)
    PULSAR_EVENTOS_MARKETPLACE: str = os.getenv(
        "PULSAR_EVENTOS_MARKETPLACE",
        "persistent://hogar/alpes/marketplace.eventos",
    )
    PULSAR_EVENTOS_VERIFICACION: str = os.getenv(
        "PULSAR_EVENTOS_VERIFICACION",
        "persistent://hogar/alpes/verificacion.eventos",
    )
    PULSAR_EVENTOS_COTIZACION: str = os.getenv(
        "PULSAR_EVENTOS_COTIZACION",
        "persistent://hogar/alpes/cotizaciones.eventos",
    )
    PULSAR_EVENTOS_NOTIFICACION: str = os.getenv(
        "PULSAR_EVENTOS_NOTIFICACION",
        "persistent://hogar/alpes/notificaciones.eventos",
    )

    # Tópicos de salida (comandos que el orquestador publica)
    PULSAR_VERIFICACION_COMANDOS: str = os.getenv(
        "PULSAR_VERIFICACION_COMANDOS",
        "persistent://hogar/alpes/verificacion.comandos",
    )
    PULSAR_COTIZACION_COMANDOS: str = os.getenv(
        "PULSAR_COTIZACION_COMANDOS",
        "persistent://hogar/alpes/cotizaciones.comandos",
    )
    PULSAR_NOTIFICACION_COMANDOS: str = os.getenv(
        "PULSAR_NOTIFICACION_COMANDOS",
        "persistent://hogar/alpes/notificaciones.comandos",
    )

    # Saga
    SAGA_MAX_RETRIES: int = int(os.getenv("SAGA_MAX_RETRIES", "3"))
    SAGA_RETRY_DELAY_SECONDS: int = int(os.getenv("SAGA_RETRY_DELAY_SECONDS", "10"))

    # URLs de servicios participantes (para compensaciones vía HTTP cuando no hay consumer Pulsar)
    MARKETPLACE_URL: str = os.getenv("MARKETPLACE_URL", "http://localhost:8000")


settings = Settings()
