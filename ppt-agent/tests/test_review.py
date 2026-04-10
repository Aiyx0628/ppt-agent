import pytest
from ppt_agent.schemas.project import ProjectCreateRequest, ProjectConfigPayload
from ppt_agent.schemas.svg import SvgSlideArtifact, SvgSlidePage
from ppt_agent.services.storage_repository import StorageRepository
from ppt_agent.services.project_service import ProjectService

VALID_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><rect width="1280" height="720" fill="#fff"/><text x="100" y="100">Hello World, 这是一段测试文字</text></svg>'
NO_VIEWBOX_SVG = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="1280" height="720" fill="#fff"/><text x="100" y="100">内容</text></svg>'
BROKEN_SVG = "<svg><broken"
EMPTY_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><rect width="1280" height="720" fill="#fff"/></svg>'


def setup_project_with_svg(service, repository, svgs: list[str]):
    project = service.create_project(ProjectCreateRequest(
        title="Review 测试",
        topic="Review 测试内容",
        config=ProjectConfigPayload(scenario="汇报", audience="团队", style_pref="简洁"),
    ))
    artifact = SvgSlideArtifact(
        project_id=project.id,
        version=1,
        pages=[
            SvgSlidePage(slide_id=f"{project.id}_s{i+1}", order_no=i+1, title=f"页{i+1}", svg=svg)
            for i, svg in enumerate(svgs)
        ],
    )
    repository.save_artifact(project.id, "svg_slide", artifact.model_dump(mode="json"))
    return project.id


def test_review_valid_svg_passes(service, repository):
    project_id = setup_project_with_svg(service, repository, [VALID_SVG])
    result = service.run_review(project_id)

    assert len(result.pages) == 1
    assert result.pages[0].passed is True
    assert result.pages[0].issues == []


def test_review_detects_no_viewbox(service, repository):
    project_id = setup_project_with_svg(service, repository, [NO_VIEWBOX_SVG])
    result = service.run_review(project_id)

    codes = [issue.code for issue in result.pages[0].issues]
    assert "missing_viewbox" in codes


def test_review_detects_broken_svg(service, repository):
    project_id = setup_project_with_svg(service, repository, [BROKEN_SVG])
    result = service.run_review(project_id)

    codes = [issue.code for issue in result.pages[0].issues]
    assert "invalid_xml" in codes
    assert result.pages[0].passed is False


def test_review_detects_no_text(service, repository):
    project_id = setup_project_with_svg(service, repository, [EMPTY_SVG])
    result = service.run_review(project_id)

    codes = [issue.code for issue in result.pages[0].issues]
    assert "no_text_content" in codes


def test_review_persists(service, repository):
    project_id = setup_project_with_svg(service, repository, [VALID_SVG])
    service.run_review(project_id)

    reloaded = service.get_review(project_id)
    assert reloaded.project_id == project_id
    assert len(reloaded.pages) == 1
