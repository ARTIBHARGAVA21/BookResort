from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.config import settings

engine_kwargs = {"future": True}
if settings.is_sqlite:
    # FastAPI can hit the SQLite connection from multiple threads.
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

if settings.is_sqlite:
    # Enforce FK constraints on SQLite (off by default).
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def transactional_session(db: Session):
    """Wrap a unit of work in a single atomic transaction.

    Usage:
        with transactional_session(db) as tx:
            ...
    Commits on success, rolls back + re-raises on any error.
    """
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
