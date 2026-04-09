from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine

from ppt_agent.config import get_settings
from ppt_agent.schemas.health import ServiceStatus

_engine: Engine | None = None


def get_engine() -> Engine | None:
    global _engine

    settings = get_settings()
    if not settings.database_url:
        return None

    if _engine is None:
        _engine = create_engine(settings.database_url, pool_pre_ping=True)

    return _engine


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
