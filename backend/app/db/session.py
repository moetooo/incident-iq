"""Engine and session factory."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.db.base import Base


def build_engine(settings: Settings) -> Engine:
    """Create a SQLAlchemy engine for the configured database URL."""
    url = settings.DATABASE_URL
    kwargs: dict[str, Any] = {"echo": settings.DATABASE_ECHO, "future": True}

    if url.startswith("sqlite"):
        # SQLite is used for local development and automated tests.
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_pre_ping"] = True
        kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
        kwargs["max_overflow"] = settings.DATABASE_POOL_SIZE

    return create_engine(url, **kwargs)


class Database:
    """Owns the engine and session factory for the application."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None

    @property
    def engine(self) -> Engine:
        """Return the lazily created engine."""
        if self._engine is None:
            self._engine = build_engine(self._settings)
        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        """Return the lazily created session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine, autoflush=False, expire_on_commit=False, future=True
            )
        return self._session_factory

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Yield a session and roll back on error."""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_all(self) -> None:
        """Create every table. Used for local development and tests only."""
        Base.metadata.create_all(bind=self.engine)


_database: Database | None = None


def get_database() -> Database:
    """Return the process-wide database wrapper."""
    global _database
    if _database is None:
        _database = Database()
    return _database


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    database = get_database()
    session = database.session_factory()
    try:
        yield session
    finally:
        session.close()
