import pytest
from pathlib import Path

from fastapi.testclient import TestClient

from ppt_agent.api.app import create_app
from ppt_agent.config import get_settings
from ppt_agent.services.project_service import ProjectService
from ppt_agent.services.storage_repository import StorageRepository


@pytest.fixture
def tmp_storage(tmp_path: Path) -> Path:
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
