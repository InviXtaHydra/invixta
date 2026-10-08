"""Database engine, session factory and the declarative base for all models."""

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SessionFactory = Callable[[], AbstractContextManager[Session]]


def get_session_factory() -> SessionFactory:
    """FastAPI dependency for work that outlives the request (the chat stream's worker thread): it opens
    its own session, so a client that disconnects mid-answer doesn't roll back what the agent saves."""
    return SessionLocal
