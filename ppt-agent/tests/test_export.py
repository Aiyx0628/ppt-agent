import zipfile
import io
import pytest
from ppt_agent.schemas.project import ProjectCreateRequest, ProjectConfigPayload
from ppt_agent.schemas.svg import SvgSlideArtifact, SvgSlidePage
from ppt_agent.services.project_service import ProjectService

MINIMAL_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><rect width="1280" height="720" fill="#fff"/><text x="100" y="100">Test</text></svg>'


def make_project_with_svg(service, repository):
    project = service.create_project(ProjectCreateRequest(
        title="导出测试",
        topic="导出测试内容",
        config=ProjectConfigPayload(scenario="汇报", audience="团队", style_pref="简洁"),
    ))
    artifact = SvgSlideArtifact(
        project_id=project.id,
        version=1,
        pages=[
            SvgSlidePage(slide_id=f"{project.id}_s1", order_no=1, title="封面", svg=MINIMAL_SVG),
            SvgSlidePage(slide_id=f"{project.id}_s2", order_no=2, title="背景", svg=MINIMAL_SVG),
        ],
    )
    repository.save_artifact(project.id, "svg_slide", artifact.model_dump(mode="json"))
    return project.id


def test_export_svg_zip_contains_all_pages(service, repository):
    project_id = make_project_with_svg(service, repository)
    zip_bytes = service.export_svg_zip(project_id)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()

    assert "slide_01.svg" in names
    assert "slide_02.svg" in names
    assert len(names) == 2


def test_export_svg_zip_file_content(service, repository):
    project_id = make_project_with_svg(service, repository)
    zip_bytes = service.export_svg_zip(project_id)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        content = zf.read("slide_01.svg").decode()

    assert "<svg" in content


def test_export_pdf_returns_bytes(service, repository):
    project_id = make_project_with_svg(service, repository)
    pdf_bytes = service.export_pdf(project_id)

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:4] == b"%PDF"
