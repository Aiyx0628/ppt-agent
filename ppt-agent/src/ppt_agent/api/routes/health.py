from datetime import UTC, datetime

from fastapi import APIRouter

from ppt_agent.config import get_settings
from ppt_agent.db import ping_database
from ppt_agent.schemas.health import HealthResponse, ServiceStatus
from ppt_agent.services.model_router import get_model_router

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    settings = get_settings()
    db_status = ping_database()
    model_status = get_model_router().health()

    return HealthResponse(
        app=settings.app_name,
        environment=settings.app_env,
        timestamp=datetime.now(UTC),
        storage_root=str(settings.storage_root),
        services={
            "api": ServiceStatus(status="ok", detail="FastAPI is serving requests."),
            "database": db_status,
            "model_router": model_status,
        },
    )
