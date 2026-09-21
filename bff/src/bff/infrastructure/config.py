import os


class Settings:
    APP_NAME: str = "bff"
    VERSION: str = "0.1.0"

    MARKETPLACE_URL: str = os.getenv("MARKETPLACE_URL", "http://localhost:8000")
    VERIFICACION_URL: str = os.getenv("VERIFICACION_URL", "http://localhost:8001")
    COTIZACION_URL: str = os.getenv("COTIZACION_URL", "http://localhost:8002")
    NOTIFICACIONES_URL: str = os.getenv("NOTIFICACIONES_URL", "http://localhost:8003")


settings = Settings()
