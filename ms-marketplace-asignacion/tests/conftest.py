import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from marketplace_asignacion.infrastructure import database as db_module
from marketplace_asignacion.infrastructure import orm  # noqa: F401 - registra tablas en Base.metadata


@pytest.fixture(scope="session", autouse=True)
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Monkeypatch infraestructura antes de importar la app
    db_module.engine = engine
    db_module.SessionLocal = SessionLocal
    db_module.Base.metadata.create_all(bind=engine)

    yield

    engine.dispose()


@pytest.fixture
def db_session(test_db):
    from marketplace_asignacion.infrastructure.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
