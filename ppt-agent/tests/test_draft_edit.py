import pytest
from ppt_agent.schemas.project import ProjectCreateRequest, ProjectConfigPayload
from ppt_agent.schemas.slide_plan import (
    SlidePlanArtifact, SlidePlanPage, SlidePlanBlock,
    SlidePlanPageUpdateRequest, SlidePlanBlockUpdate,
)
from ppt_agent.services.storage_repository import StorageRepository
from ppt_agent.services.project_service import ProjectService


def make_project(service: ProjectService) -> str:
    project = service.create_project(ProjectCreateRequest(
        title="测试项目",
        topic="这是一个测试",
        config=ProjectConfigPayload(
            scenario="汇报", audience="团队", style_pref="简洁",
        ),
    ))
    return project.id


def seed_slide_plan(repository: StorageRepository, project_id: str) -> SlidePlanArtifact:
    artifact = SlidePlanArtifact(
        project_id=project_id,
        version=1,
        pages=[
            SlidePlanPage(
                slide_id=f"{project_id}_s1",
                order_no=1,
                title="封面",
                narrative_role="开场",
                core_message="核心消息",
                visual_focus="标题区",
                suggested_layout="cover",
                design_notes=[],
                blocks=[
                    SlidePlanBlock(
                        block_id="b1",
                        kind="text",
                        title="标题块",
                        content="原始内容",
                        words_budget=50,
                        emphasis="high",
                    )
                ],
            )
        ],
    )
    repository.save_artifact(project_id, "slide_plan", artifact.model_dump(mode="json"))
    return artifact


def test_update_slide_plan_page_title(service: ProjectService, repository: StorageRepository):
    project_id = make_project(service)
    seed_slide_plan(repository, project_id)

    updated = service.update_slide_plan_page(
        project_id,
        f"{project_id}_s1",
        SlidePlanPageUpdateRequest(title="新标题"),
    )

    assert updated.title == "新标题"
    assert updated.core_message == "核心消息"  # 未改的字段保持不变


def test_update_slide_plan_page_blocks(service: ProjectService, repository: StorageRepository):
    project_id = make_project(service)
    seed_slide_plan(repository, project_id)

    updated = service.update_slide_plan_page(
        project_id,
        f"{project_id}_s1",
        SlidePlanPageUpdateRequest(
            blocks=[SlidePlanBlockUpdate(block_id="b1", content="新内容")]
        ),
    )

    assert updated.blocks[0].content == "新内容"
    assert updated.blocks[0].title == "标题块"  # 未改字段保持不变


def test_update_slide_plan_page_persists(service: ProjectService, repository: StorageRepository):
    project_id = make_project(service)
    seed_slide_plan(repository, project_id)

    service.update_slide_plan_page(
        project_id,
        f"{project_id}_s1",
        SlidePlanPageUpdateRequest(title="持久化标题"),
    )

    reloaded = service.get_slide_plan(project_id)
    assert reloaded.pages[0].title == "持久化标题"


def test_update_nonexistent_block_raises(service: ProjectService, repository: StorageRepository):
    project_id = make_project(service)
    seed_slide_plan(repository, project_id)

    from ppt_agent.services.storage_repository import ProjectNotFoundError
    with pytest.raises(ProjectNotFoundError, match="Unknown block_ids"):
        service.update_slide_plan_page(
            project_id,
            f"{project_id}_s1",
            SlidePlanPageUpdateRequest(
                blocks=[SlidePlanBlockUpdate(block_id="nonexistent", content="x")]
            ),
        )


def test_update_empty_payload_changes_nothing(service: ProjectService, repository: StorageRepository):
    project_id = make_project(service)
    seed_slide_plan(repository, project_id)

    updated = service.update_slide_plan_page(
        project_id,
        f"{project_id}_s1",
        SlidePlanPageUpdateRequest(),  # 全部 None
    )

    assert updated.title == "封面"
    assert updated.blocks[0].content == "原始内容"
