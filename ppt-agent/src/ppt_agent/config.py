from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DeckFlow API"
    app_env: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    api_prefix: str = "/api"
    frontend_origin: str = "http://127.0.0.1:5173"
    database_url: str | None = None
    storage_root: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[3] / "storage"
    )

    model_config = SettingsConfigDict(
        env_prefix="PPT_AGENT_",
        env_file=".env",
        extra="ignore",
    )

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
