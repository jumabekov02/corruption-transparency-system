from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# The "engine" is the actual connection pool to Postgres.
# pool_pre_ping checks a connection is alive before using it (avoids stale-connection errors).
engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

# A "session" is one unit of work (a conversation with the DB). SessionLocal is a factory
# that produces a new session each time we call it.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: open a session for one request, then always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
