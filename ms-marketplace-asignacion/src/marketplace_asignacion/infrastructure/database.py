from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from marketplace_asignacion.infrastructure.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.ECHO_SQL,
    connect_args={"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
