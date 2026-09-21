from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from generador_cotizacion.infrastructure.config import settings
from generador_cotizacion.infrastructure.database import Base

# Engine/sesión alternativos que demuestran que la persistencia puede
# implementarse sobre MySQL en lugar de PostgreSQL, reutilizando el mismo
# `Base` declarativo (y por lo tanto los mismos modelos ORM) definidos para
# la implementación con SQLAlchemy/PostgreSQL en `database.py` y `orm.py`.
mysql_engine = create_engine(
    settings.MYSQL_DATABASE_URL,
    echo=settings.ECHO_SQL,
    pool_pre_ping=True,
)
MySQLSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=mysql_engine)
