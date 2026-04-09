from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ppt_agent.config import get_settings
from ppt_agent.db_models import Base
from ppt_agent.schemas.health import ServiceStatus

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_schema_initialized = False


def get_engine() -> Engine | None:
    global _engine

    settings = get_settings()
    if not settings.database_url:
        return None

    if _engine is None:
        _engine = create_engine(settings.database_url, pool_pre_ping=True)

    return _engine


def get_session_factory() -> sessionmaker[Session] | None:
    global _schema_initialized, _session_factory

    engine = get_engine()
    if engine is None:
        return None

    settings = get_settings()
    if settings.database_auto_create and not _schema_initialized:
        Base.metadata.create_all(engine)
        _schema_initialized = True

    if _session_factory is None:
        _session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    return _session_factory


def create_database_schema() -> ServiceStatus:
    global _schema_initialized

    engine = get_engine()
    if engine is None:
        return ServiceStatus(
            status="not_configured",
            detail="Set PPT_AGENT_DATABASE_URL to enable PostgreSQL schema creation.",
        )

    try:
        Base.metadata.create_all(engine)
        _schema_initialized = True
    except SQLAlchemyError as exc:
        return ServiceStatus(status="error", detail=str(exc))

    return ServiceStatus(status="ok", detail="Database schema is ready.")


def ping_database() -> ServiceStatus:
    engine = get_engine()
    if engine is None:
        return ServiceStatus(
            status="not_configured",
            detail="Set PPT_AGENT_DATABASE_URL to enable PostgreSQL health checks.",
        )

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return ServiceStatus(status="error", detail=str(exc))

    return ServiceStatus(status="ok", detail="PostgreSQL connection healthy.")
