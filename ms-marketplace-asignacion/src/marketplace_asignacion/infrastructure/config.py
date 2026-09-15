import os
from typing import Optional


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://hogar:alpes@localhost:5432/marketplace_db",
    )
    ECHO_SQL: bool = os.getenv("ECHO_SQL", "false").lower() == "true"
    IDEMPOTENCY_TTL_SECONDS: int = int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "86400"))
    APP_NAME: str = "marketplace-asignacion"
    VERSION: str = "0.1.0"

    PULSAR_SERVICE_URL: str = os.getenv("PULSAR_SERVICE_URL", "pulsar://localhost:6650")
    PULSAR_PRODUCER_TOPIC: str = os.getenv(
        "PULSAR_PRODUCER_TOPIC",
        "persistent://hogar/alpes/marketplace.eventos",
    )
    PULSAR_VERIFICACION_TOPIC: str = os.getenv(
        "PULSAR_VERIFICACION_TOPIC",
        "persistent://hogar/alpes/verificacion.comandos",
    )
    PULSAR_COTIZACIONES_TOPIC: str = os.getenv(
        "PULSAR_COTIZACIONES_TOPIC",
        "persistent://hogar/alpes/cotizaciones.comandos",
    )
    PULSAR_NOTIFICACIONES_TOPIC: str = os.getenv(
        "PULSAR_NOTIFICACIONES_TOPIC",
        "persistent://hogar/alpes/notificaciones.comandos",
    )


settings = Settings()
