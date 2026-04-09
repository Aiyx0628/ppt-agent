from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ProjectStatus = Literal[
    "draft",
    "briefing",
    "brief_confirmed",
    "outline_ready",
]


class ProjectConfigPayload(BaseModel):
    scenario: str
    audience: str
    style_pref: str
    page_limit: int = Field(default=8, ge=4, le=30)
    research_enabled: bool = True
    narration_enabled: bool = False


class ProjectCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    topic: str = Field(min_length=3, max_length=200)
    config: ProjectConfigPayload


class ProjectUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    topic: str | None = Field(default=None, min_length=3, max_length=200)
    config: ProjectConfigPayload | None = None
    status: ProjectStatus | None = None


class ProjectResponse(BaseModel):
    id: str
    title: str
    topic: str
    status: ProjectStatus
    config: ProjectConfigPayload
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
