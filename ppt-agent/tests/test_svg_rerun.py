import pytest
from ppt_agent.schemas.project import ProjectCreateRequest, ProjectConfigPayload
from ppt_agent.schemas.slide_plan import SlidePlanArtifact, SlidePlanPage, SlidePlanBlock
from ppt_agent.schemas.svg import SvgSlideArtifact, SvgSlidePage
from ppt_agent.services.storage_repository import StorageRepository
from ppt_agent.services.project_service import ProjectService


def make_project(service):
    project = service.create_project(ProjectCreateRequest(
        title="SVG 重跑测试",
        topic="测试内容",
        config=ProjectConfigPayload(scenario="汇报", audience="团队", style_pref="简洁"),
    ))
    return project.id


def seed_slide_plan(repository, project_id):
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
                blocks=[SlidePlanBlock(block_id="b1", kind="text", title="标题", content="内容", words_budget=50, emphasis="high")],
            ),
            SlidePlanPage(
                slide_id=f"{project_id}_s2",
                order_no=2,
                title="背景",
                narrative_role="说明背景",
                core_message="背景消息",
                visual_focus="背景区",
                suggested_layout="content",
                design_notes=[],
                blocks=[SlidePlanBlock(block_id="b2", kind="text", title="背景块", content="背景内容", words_budget=50, emphasis="medium")],
            ),
        ],
    )
    repository.save_artifact(project_id, "slide_plan", artifact.model_dump(mode="json"))


def seed_svg(repository, project_id):
    artifact = SvgSlideArtifact(
        project_id=project_id,
        version=1,
        pages=[
            SvgSlidePage(slide_id=f"{project_id}_s1", order_no=1, title="封面", svg="<svg>原始SVG1</svg>"),
            SvgSlidePage(slide_id=f"{project_id}_s2", order_no=2, title="背景", svg="<svg>原始SVG2</svg>"),
        ],
    )
    repository.save_artifact(project_id, "svg_slide", artifact.model_dump(mode="json"))


def test_regenerate_svg_page_only_updates_target(service, repository):
    project_id = make_project(service)
    seed_slide_plan(repository, project_id)
    seed_svg(repository, project_id)

    result = service.regenerate_svg_page(project_id, f"{project_id}_s1")

    assert result.slide_id == f"{project_id}_s1"
    reloaded = service.get_svg(project_id)
    assert reloaded.pages[1].slide_id == f"{project_id}_s2"
    assert len(reloaded.pages) == 2


def test_regenerate_svg_page_persists(service, repository):
    project_id = make_project(service)
    seed_slide_plan(repository, project_id)
    seed_svg(repository, project_id)

    service.regenerate_svg_page(project_id, f"{project_id}_s1")

    reloaded = service.get_svg(project_id)
    assert reloaded.pages[0].slide_id == f"{project_id}_s1"
