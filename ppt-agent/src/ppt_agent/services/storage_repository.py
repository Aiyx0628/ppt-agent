import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ppt_agent.db import get_session_factory
from ppt_agent.db_models import ArtifactRecord, ProjectConfigRecord, ProjectRecord
from ppt_agent.schemas.project import ProjectResponse, ProjectUpdateRequest


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
        self._sync_project_record(project)
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
        self._sync_project_record(updated)
        return updated

    def delete_project(self, project_id: str) -> None:
        project_dir = self._project_dir(project_id)
        if not project_dir.exists():
            raise ProjectNotFoundError(f"Project {project_id} not found.")
        shutil.rmtree(project_dir)
        self._delete_project_record(project_id)

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
        target = artifact_dir / f"v{version}.json"
        self._write_json(target, stored)
        self._record_artifact(project_id, artifact_type, version, target)
        return stored

    def save_source_file(self, project_id: str, filename: str, content: bytes) -> Path:
        source_dir = self._project_dir(project_id) / "sources"
        source_dir.mkdir(parents=True, exist_ok=True)
        safe_name = self._safe_filename(filename)
        target = source_dir / safe_name
        target.write_bytes(content)
        return target

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

    def _safe_filename(self, filename: str) -> str:
        candidate = Path(filename or "upload.bin").name
        normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", candidate).strip("._")
        return normalized or "upload.bin"

    def _sync_project_record(self, project: ProjectResponse) -> None:
        session_factory = get_session_factory()
        if session_factory is None:
            return

        with session_factory() as session:
            record = session.get(ProjectRecord, project.id)
            if record is None:
                record = ProjectRecord(
                    id=project.id,
                    title=project.title,
                    topic=project.topic,
                    status=project.status,
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                )
                record.config = ProjectConfigRecord(
                    project_id=project.id,
                    scenario=project.config.scenario,
                    audience=project.config.audience,
                    style_pref=project.config.style_pref,
                    page_limit=project.config.page_limit,
                    research_enabled=project.config.research_enabled,
                    narration_enabled=project.config.narration_enabled,
                )
                session.add(record)
            else:
                record.title = project.title
                record.topic = project.topic
                record.status = project.status
                record.created_at = project.created_at
                record.updated_at = project.updated_at
                if record.config is None:
                    record.config = ProjectConfigRecord(project_id=project.id)
                record.config.scenario = project.config.scenario
                record.config.audience = project.config.audience
                record.config.style_pref = project.config.style_pref
                record.config.page_limit = project.config.page_limit
                record.config.research_enabled = project.config.research_enabled
                record.config.narration_enabled = project.config.narration_enabled
            session.commit()

    def _delete_project_record(self, project_id: str) -> None:
        session_factory = get_session_factory()
        if session_factory is None:
            return

        with session_factory() as session:
            record = session.get(ProjectRecord, project_id)
            if record is not None:
                session.delete(record)
                session.commit()

    def _record_artifact(
        self,
        project_id: str,
        artifact_type: str,
        version: int,
        storage_path: Path,
    ) -> None:
        session_factory = get_session_factory()
        if session_factory is None:
            return

        with session_factory() as session:
            record = session.execute(
                select(ArtifactRecord).where(
                    ArtifactRecord.project_id == project_id,
                    ArtifactRecord.artifact_type == artifact_type,
                    ArtifactRecord.version == version,
                )
            ).scalar_one_or_none()
            if record is None:
                session.add(
                    ArtifactRecord(
                        project_id=project_id,
                        artifact_type=artifact_type,
                        version=version,
                        storage_path=str(storage_path),
                        created_at=datetime.now(UTC),
                    )
                )
            else:
                record.storage_path = str(storage_path)
            session.commit()
