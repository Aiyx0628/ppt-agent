from typing import Any

from pydantic import BaseModel, Field


class ModelProviderStatus(BaseModel):
    provider: str
    configured: bool
    default_model: str | None = None
    base_url: str


class ModelProvidersResponse(BaseModel):
    default_provider: str
    providers: list[ModelProviderStatus]


class GenerateTextRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)
    provider: str | None = None
    model: str | None = None
    system_instruction: str | None = Field(default=None, max_length=4000)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_output_tokens: int | None = Field(default=None, ge=1, le=8192)


class GenerateTextResponse(BaseModel):
    provider: str
    model: str
    text: str
    raw: dict[str, Any]
