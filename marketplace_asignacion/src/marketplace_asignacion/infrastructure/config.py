import os
from typing import Optional


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./marketplace_asignacion.db",
    )
    ECHO_SQL: bool = os.getenv("ECHO_SQL", "false").lower() == "true"
    IDEMPOTENCY_TTL_SECONDS: int = int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "86400"))
    APP_NAME: str = "marketplace-asignacion"
    VERSION: str = "0.1.0"


settings = Settings()
