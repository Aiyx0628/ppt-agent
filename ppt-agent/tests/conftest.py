import pytest
from pathlib import Path

from fastapi.testclient import TestClient

import ppt_agent.db as _db_module
from ppt_agent.api.app import create_app
from ppt_agent.config import get_settings
from ppt_agent.services.project_service import ProjectService
from ppt_agent.services.storage_repository import StorageRepository


@pytest.fixture
def tmp_storage(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setenv("PPT_AGENT_DATABASE_URL", "")
    monkeypatch.setenv("PPT_AGENT_STORAGE_ROOT", str(tmp_path / "storage"))
    get_settings.cache_clear()
    # Reset cached DB engine so it won't try to connect
    monkeypatch.setattr(_db_module, "_engine", None)
    monkeypatch.setattr(_db_module, "_session_factory", None)
    monkeypatch.setattr(_db_module, "_schema_initialized", False)
    return tmp_path / "storage"


@pytest.fixture
def repository(tmp_storage: Path) -> StorageRepository:
    return StorageRepository(tmp_storage)


@pytest.fixture
def service(repository: StorageRepository) -> ProjectService:
    return ProjectService(repository)


@pytest.fixture
def client(tmp_storage: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PPT_AGENT_STORAGE_ROOT", str(tmp_storage))
    monkeypatch.setenv("PPT_AGENT_DATABASE_AUTO_CREATE", "false")
    get_settings.cache_clear()
    app = create_app()
    return TestClient(app)
