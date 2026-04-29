from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        database_url = settings.sqlalchemy_database_url
        if not database_url:
            raise RuntimeError("DATABASE_URL is not configured.")

        _engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            future=True,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
            class_=Session,
            expire_on_commit=False,
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> dict:
    if not settings.sqlalchemy_database_url:
        return {
            "ok": False,
            "configured": False,
            "message": "DATABASE_URL is not configured.",
        }

    try:
        with get_engine().connect() as connection:
            result = connection.execute(text("SELECT 1"))
            scalar = result.scalar_one()
        return {
            "ok": scalar == 1,
            "configured": True,
            "message": "Database connection successful.",
        }
    except Exception as exc:
        return {
            "ok": False,
            "configured": True,
            "message": "Database connection failed.",
            "error": str(exc),
        }
