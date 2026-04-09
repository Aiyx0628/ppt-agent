from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import httpx

from ppt_agent.config import Settings, get_settings
from ppt_agent.schemas.health import ServiceStatus
from ppt_agent.schemas.model import (
    GenerateTextRequest,
    GenerateTextResponse,
    ModelProviderStatus,
    ModelProvidersResponse,
)


class ModelProviderError(RuntimeError):
    pass


class UnsupportedProviderError(ModelProviderError):
    pass


class ProviderNotConfiguredError(ModelProviderError):
    pass


class LLMProvider(Protocol):
    provider_name: str

    def generate_text(self, request: GenerateTextRequest) -> GenerateTextResponse:
        ...


@dataclass(slots=True)
class OpenAIProvider:
    settings: Settings
    provider_name: str = "openai"

    def generate_text(self, request: GenerateTextRequest) -> GenerateTextResponse:
        api_key = self.settings.openai_api_key
        model = request.model or self.settings.openai_model
        if not api_key or not model:
            raise ProviderNotConfiguredError("OpenAI provider is not fully configured.")

        payload: dict[str, object] = {
            "model": model,
            "input": request.prompt,
        }
        if request.system_instruction:
            payload["instructions"] = request.system_instruction
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_output_tokens is not None:
            payload["max_output_tokens"] = request.max_output_tokens

        response = httpx.post(
            f"{self.settings.openai_base_url.rstrip('/')}/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.settings.model_timeout_seconds,
        )
        response.raise_for_status()
        raw = response.json()
        text = raw.get("output_text") or _extract_openai_output_text(raw)
        return GenerateTextResponse(
            provider=self.provider_name,
            model=model,
            text=text,
            raw=raw,
        )


@dataclass(slots=True)
class GeminiProvider:
    settings: Settings
    provider_name: str = "gemini"

    def generate_text(self, request: GenerateTextRequest) -> GenerateTextResponse:
        api_key = self.settings.gemini_api_key
        model = request.model or self.settings.gemini_model
        if not api_key or not model:
            raise ProviderNotConfiguredError("Gemini provider is not fully configured.")

        payload: dict[str, object] = {
            "contents": [
                {
                    "parts": [{"text": request.prompt}],
                }
            ]
        }
        if request.system_instruction:
            payload["system_instruction"] = {
                "parts": [{"text": request.system_instruction}],
            }
        if request.temperature is not None or request.max_output_tokens is not None:
            generation_config: dict[str, object] = {}
            if request.temperature is not None:
                generation_config["temperature"] = request.temperature
            if request.max_output_tokens is not None:
                generation_config["maxOutputTokens"] = request.max_output_tokens
            payload["generationConfig"] = generation_config

        response = httpx.post(
            f"{self.settings.gemini_base_url.rstrip('/')}/models/{model}:generateContent",
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=self.settings.model_timeout_seconds,
        )
        response.raise_for_status()
        raw = response.json()
        text = _extract_gemini_text(raw)
        return GenerateTextResponse(
            provider=self.provider_name,
            model=model,
            text=text,
            raw=raw,
        )


class ModelRouter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.providers: dict[str, LLMProvider] = {
            "openai": OpenAIProvider(settings),
            "gemini": GeminiProvider(settings),
        }

    def get_provider(self, provider_name: str | None = None) -> LLMProvider:
        name = (provider_name or self.settings.default_model_provider).lower()
        provider = self.providers.get(name)
        if provider is None:
            raise UnsupportedProviderError(f"Unsupported model provider: {name}")
        return provider

    def generate_text(self, request: GenerateTextRequest) -> GenerateTextResponse:
        provider = self.get_provider(request.provider)
        return provider.generate_text(request)

    def describe_providers(self) -> ModelProvidersResponse:
        return ModelProvidersResponse(
            default_provider=self.settings.default_model_provider,
            providers=[
                ModelProviderStatus(
                    provider="openai",
                    configured=bool(self.settings.openai_api_key and self.settings.openai_model),
                    default_model=self.settings.openai_model,
                    base_url=self.settings.openai_base_url,
                ),
                ModelProviderStatus(
                    provider="gemini",
                    configured=bool(self.settings.gemini_api_key and self.settings.gemini_model),
                    default_model=self.settings.gemini_model,
                    base_url=self.settings.gemini_base_url,
                ),
            ],
        )

    def health(self) -> ServiceStatus:
        providers = self.describe_providers().providers
        configured = [provider.provider for provider in providers if provider.configured]
        if not configured:
            return ServiceStatus(
                status="not_configured",
                detail="Configure PPT_AGENT_OPENAI_* or PPT_AGENT_GEMINI_* to enable model calls.",
            )

        return ServiceStatus(
            status="ok",
            detail=f"Configured providers: {', '.join(configured)}.",
        )


def _extract_openai_output_text(raw: dict[str, object]) -> str:
    output = raw.get("output")
    if not isinstance(output, list):
        return ""

    texts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            text = block.get("text")
            if isinstance(text, str):
                texts.append(text)
    return "\n".join(texts).strip()


def _extract_gemini_text(raw: dict[str, object]) -> str:
    candidates = raw.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ""

    first = candidates[0]
    if not isinstance(first, dict):
        return ""
    content = first.get("content")
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""

    texts = [part.get("text") for part in parts if isinstance(part, dict) and isinstance(part.get("text"), str)]
    return "\n".join(texts).strip()


@lru_cache
def get_model_router() -> ModelRouter:
    return ModelRouter(get_settings())
