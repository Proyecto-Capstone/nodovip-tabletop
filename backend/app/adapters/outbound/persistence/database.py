"""Conexión a PostgreSQL con SQLAlchemy 2.0 (adaptador de salida)."""

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base de todos los modelos ORM."""


def get_database_url() -> str:
    """Lee DATABASE_URL y fuerza el driver psycopg 3.

    docker-compose entrega `postgresql://...`; SQLAlchemy necesita
    `postgresql+psycopg://...` para usar psycopg 3.
    """
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("Falta la variable de entorno DATABASE_URL")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(get_database_url(), pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False)
    return _engine


def get_session() -> Iterator[Session]:
    """Dependencia de FastAPI: abre una sesión por request y la cierra al final."""
    get_engine()
    assert _SessionLocal is not None
    with _SessionLocal() as session:
        yield session
