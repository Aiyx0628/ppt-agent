import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ppt_agent.schemas.project import ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest


class ProjectNotFoundError(Exception):
    pass


class StorageRepository:
    def __init__(self, storage_root: Path):
        self.storage_root = storage_root
        self.projects_root = storage_root / "projects"
        self.projects_root.mkdir(parents=True, exist_ok=True)

    def list_projects(self) -> list[ProjectResponse]:
        projects: list[ProjectResponse] = []
        for metadata_path in sorted(self.projects_root.glob("*/project.json")):
            projects.append(ProjectResponse.model_validate_json(metadata_path.read_text()))

        return sorted(projects, key=lambda item: item.updated_at, reverse=True)

    def create_project(self, project: ProjectResponse) -> ProjectResponse:
        project_dir = self._project_dir(project.id)
        project_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(project_dir / "project.json", project.model_dump(mode="json"))
        return project

    def get_project(self, project_id: str) -> ProjectResponse:
        metadata_path = self._project_dir(project_id) / "project.json"
        if not metadata_path.exists():
            raise ProjectNotFoundError(f"Project {project_id} not found.")
        return ProjectResponse.model_validate_json(metadata_path.read_text())

    def update_project(
        self, project_id: str, payload: ProjectUpdateRequest
    ) -> ProjectResponse:
        current = self.get_project(project_id)
        updated = current.model_copy(
            update={
                "title": payload.title if payload.title is not None else current.title,
                "topic": payload.topic if payload.topic is not None else current.topic,
                "config": payload.config if payload.config is not None else current.config,
                "status": payload.status if payload.status is not None else current.status,
                "updated_at": datetime.now(UTC),
            }
        )
        self._write_json(
            self._project_dir(project_id) / "project.json",
            updated.model_dump(mode="json"),
        )
        return updated

    def delete_project(self, project_id: str) -> None:
        project_dir = self._project_dir(project_id)
        if not project_dir.exists():
            raise ProjectNotFoundError(f"Project {project_id} not found.")
        shutil.rmtree(project_dir)

    def load_artifact(self, project_id: str, artifact_type: str) -> dict[str, Any]:
        artifact_dir = self._artifact_dir(project_id, artifact_type)
        latest = self._latest_version_path(artifact_dir)
        if latest is None:
            raise ProjectNotFoundError(
                f"{artifact_type} for project {project_id} not found."
            )
        return json.loads(latest.read_text())

    def save_artifact(
        self, project_id: str, artifact_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        artifact_dir = self._artifact_dir(project_id, artifact_type)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        version = self._next_version(artifact_dir)
        stored = {**payload, "version": version}
        self._write_json(artifact_dir / f"v{version}.json", stored)
        return stored

    def _project_dir(self, project_id: str) -> Path:
        return self.projects_root / project_id

    def _artifact_dir(self, project_id: str, artifact_type: str) -> Path:
        return self._project_dir(project_id) / "artifacts" / artifact_type

    def _latest_version_path(self, artifact_dir: Path) -> Path | None:
        candidates = sorted(artifact_dir.glob("v*.json"))
        return candidates[-1] if candidates else None

    def _next_version(self, artifact_dir: Path) -> int:
        latest = self._latest_version_path(artifact_dir)
        if latest is None:
            return 1
        return int(latest.stem.removeprefix("v")) + 1

    def _write_json(self, target: Path, payload: dict[str, Any]) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=True, indent=2))
