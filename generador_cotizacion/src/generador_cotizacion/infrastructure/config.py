import os


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://hogar:alpes@localhost:5432/cotizacion_db",
    )
    ECHO_SQL: bool = os.getenv("ECHO_SQL", "false").lower() == "true"

    # URL alternativa para demostrar que la persistencia también puede
    # implementarse sobre MySQL en lugar de PostgreSQL (ver infrastructure/mysql_*.py).
    MYSQL_DATABASE_URL: str = os.getenv(
        "MYSQL_DATABASE_URL",
        "mysql+pymysql://hogar:alpes@localhost:3306/cotizacion_db",
    )
    IDEMPOTENCY_TTL_SECONDS: int = int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "86400"))
    APP_NAME: str = "generador-cotizacion"
    VERSION: str = "0.1.0"

    PULSAR_SERVICE_URL: str = os.getenv("PULSAR_SERVICE_URL", "pulsar://localhost:6650")
    PULSAR_SUBSCRIPTION: str = os.getenv("PULSAR_SUBSCRIPTION", "cotizacion-sub")
    PULSAR_CONSUMER_TOPICS: str = os.getenv(
        "PULSAR_CONSUMER_TOPICS",
        "persistent://hogar/alpes/cotizaciones.comandos",
    )
    PULSAR_PRODUCER_TOPIC: str = os.getenv(
        "PULSAR_PRODUCER_TOPIC",
        "persistent://hogar/alpes/cotizaciones.eventos",
    )
    PULSAR_DLQ_TOPIC: str = os.getenv(
        "PULSAR_DLQ_TOPIC",
        "persistent://hogar/alpes/dlq",
    )
    PULSAR_MAX_REDELIVER_COUNT: int = int(os.getenv("PULSAR_MAX_REDELIVER_COUNT", "5"))


settings = Settings()
