import os


class Settings:
    APP_NAME: str = "ms-notificaciones"
    VERSION: str = "0.1.0"

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./ms-notificaciones.db",
    )
    ECHO_SQL: bool = os.getenv("ECHO_SQL", "false").lower() == "true"

    # Cluster de Pulsar: lo despliega el equipo, este servicio solo se conecta.
    # Vacio = arranca sin consumir comandos (solo sirve queries HTTP).
    PULSAR_SERVICE_URL: str = os.getenv("PULSAR_SERVICE_URL", "")
    PULSAR_TENANT: str = os.getenv("PULSAR_TENANT", "hogar")
    PULSAR_NAMESPACE: str = os.getenv("PULSAR_NAMESPACE", "alpes")
    PULSAR_SUSCRIPCION: str = os.getenv("PULSAR_SUSCRIPCION", "ms-notificaciones-workers")

    @property
    def TOPICO_COMANDOS(self) -> str:
        return f"persistent://{self.PULSAR_TENANT}/{self.PULSAR_NAMESPACE}/ms-notificaciones.comandos"


settings = Settings()
