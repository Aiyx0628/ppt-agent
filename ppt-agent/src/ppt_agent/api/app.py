from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ppt_agent.api.routes import router
from ppt_agent.config import get_settings
from ppt_agent.db import create_database_schema
from ppt_agent.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    configure_logging(settings.app_env)
    logger = get_logger(__name__)
    if settings.database_auto_create:
        schema_status = create_database_schema()
        logger.info(
            "deckflow.api.database_schema",
            status=schema_status.status,
            detail=schema_status.detail,
        )
    logger.info(
        "deckflow.api.startup",
        environment=settings.app_env,
        storage_root=str(settings.storage_root),
    )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix=settings.api_prefix)
    return app
