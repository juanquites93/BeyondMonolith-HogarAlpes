"""Configuración de base de datos."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from verificacion_acreditacion.infrastructure.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.ECHO_SQL,
    connect_args={"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
