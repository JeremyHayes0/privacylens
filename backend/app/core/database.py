from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# pool_pre_ping issues a lightweight "is this connection still alive"
# check before handing a pooled connection to a request. Without it, a
# connection that Postgres (or a network blip) silently closed can be
# handed out and fail on first use — pool_pre_ping trades a tiny bit of
# latency for avoiding that whole class of intermittent errors.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base. Every ORM model inherits from this."""

    pass


def get_database_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields one database session per request and
    guarantees it is closed afterward — including when the request
    raises an exception.

    This is the single seam through which all database access flows.
    Routes and services never construct their own Session; they always
    receive one via `Depends(get_database_session)`. That keeps
    connection lifecycle management in exactly one place and makes it
    trivial to swap in a different session (e.g. a test database) via
    FastAPI's dependency override mechanism.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
