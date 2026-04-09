from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ServiceStatus(BaseModel):
    status: Literal["ok", "error", "degraded", "not_configured"]
    detail: str


class HealthResponse(BaseModel):
    app: str
    environment: str
    timestamp: datetime
    storage_root: str
    services: dict[str, ServiceStatus]
