"""Fixtures compartidas para tests del orquestador."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ms_orquestador.infrastructure.database import Base


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def session_factory(test_db):
    def _factory():
        return sessionmaker(bind=test_db.bind)()

    return _factory
