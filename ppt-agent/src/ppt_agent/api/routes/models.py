from fastapi import APIRouter, HTTPException, status
import httpx

from ppt_agent.schemas.model import (
    GenerateTextRequest,
    GenerateTextResponse,
    ModelProvidersResponse,
)
from ppt_agent.services.model_router import (
    ModelProviderError,
    ProviderNotConfiguredError,
    UnsupportedProviderError,
    get_model_router,
)

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/providers", response_model=ModelProvidersResponse)
def list_model_providers() -> ModelProvidersResponse:
    return get_model_router().describe_providers()


@router.post(
    "/generate",
    response_model=GenerateTextResponse,
    status_code=status.HTTP_200_OK,
)
def generate_text(payload: GenerateTextRequest) -> GenerateTextResponse:
    router_service = get_model_router()
    try:
        return router_service.generate_text(payload)
    except UnsupportedProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProviderNotConfiguredError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Provider returned HTTP {exc.response.status_code}: {exc.response.text}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ModelProviderError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
