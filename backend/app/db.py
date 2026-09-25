"""SQLAlchemy engine a session pro čtení z existující databáze."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency - jedna DB session na request, vždy uzavřená."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
