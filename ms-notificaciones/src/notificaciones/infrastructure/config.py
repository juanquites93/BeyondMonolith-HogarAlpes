import os
import socket


class Settings:
    APP_NAME: str = "ms-notificaciones"
    VERSION: str = "0.1.0"

    PORT: int = int(os.getenv("PORT", "8000"))
    # Identifica esta replica en logs/headers. Por defecto usa el hostname del
    # proceso (en Docker, eso es el ID del contenedor), asi que no hace falta
    # configurarlo a mano salvo que el experimento necesite un nombre fijo.
    INSTANCE_ID: str = os.getenv("INSTANCE_ID", socket.gethostname())

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

    # Si se definen, reemplazan el nombre completo del topico calculado abajo.
    # El contrato real entre microservicios sigue siendo tenant/namespace; esto
    # solo existe para poder apuntar el experimento a un topico propio sin
    # tocar la suscripcion/topico que usa el despliegue real.
    _TOPICO_COMANDOS_OVERRIDE: str = os.getenv("TOPICO_COMANDOS", "")
    _TOPICO_EVENTOS_OVERRIDE: str = os.getenv("TOPICO_EVENTOS", "")

    @property
    def TOPICO_COMANDOS(self) -> str:
        if self._TOPICO_COMANDOS_OVERRIDE:
            return self._TOPICO_COMANDOS_OVERRIDE
        # Nombre de topico fijado por el contrato entre microservicios: no
        # lleva el prefijo "ms-" del nombre de este servicio/carpeta.
        return f"persistent://{self.PULSAR_TENANT}/{self.PULSAR_NAMESPACE}/notificaciones.comandos"

    @property
    def TOPICO_EVENTOS(self) -> str:
        if self._TOPICO_EVENTOS_OVERRIDE:
            return self._TOPICO_EVENTOS_OVERRIDE
        return f"persistent://{self.PULSAR_TENANT}/{self.PULSAR_NAMESPACE}/notificaciones.eventos"


settings = Settings()
