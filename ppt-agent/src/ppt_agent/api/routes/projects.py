from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status

from ppt_agent.schemas.brief import BriefConfirmResponse, BriefUpdateRequest, RequirementBrief
from ppt_agent.schemas.outline import OutlineArtifact, OutlineReorderRequest
from ppt_agent.schemas.project import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from ppt_agent.schemas.research import ResearchPack
from ppt_agent.schemas.search import SearchArtifact
from ppt_agent.schemas.slide_plan import SlidePlanArtifact
from ppt_agent.schemas.svg import SvgSlideArtifact
from ppt_agent.services.project_service import ProjectNotFoundError, get_project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
def list_projects() -> ProjectListResponse:
    service = get_project_service()
    return ProjectListResponse(items=service.list_projects())


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreateRequest) -> ProjectResponse:
    service = get_project_service()
    return service.create_project(payload)


@router.post("/intake", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project_from_intake(
    prompt: str = Form(...),
    files: list[UploadFile] = File(default=[]),
) -> ProjectResponse:
    service = get_project_service()
    uploads: list[tuple[str, bytes]] = []
    for file in files:
        uploads.append((file.filename or "upload.bin", await file.read()))
    try:
        return service.create_project_from_intake(prompt, uploads)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str) -> ProjectResponse:
    service = get_project_service()
    try:
        return service.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, payload: ProjectUpdateRequest) -> ProjectResponse:
    service = get_project_service()
    try:
        return service.update_project(project_id, payload)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str) -> Response:
    service = get_project_service()
    try:
        service.delete_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{project_id}/research/run", response_model=ResearchPack)
def run_research(project_id: str) -> ResearchPack:
    service = get_project_service()
    try:
        return service.generate_research(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{project_id}/research", response_model=ResearchPack)
def get_research(project_id: str) -> ResearchPack:
    service = get_project_service()
    try:
        return service.get_research(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{project_id}/search/generate", response_model=SearchArtifact)
def generate_search(project_id: str) -> SearchArtifact:
    service = get_project_service()
    try:
        return service.generate_search_pages(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{project_id}/search", response_model=SearchArtifact)
def get_search(project_id: str) -> SearchArtifact:
    service = get_project_service()
    try:
        return service.get_search_pages(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{project_id}/brief/generate", response_model=RequirementBrief)
def generate_brief(project_id: str) -> RequirementBrief:
    service = get_project_service()
    try:
        return service.generate_brief(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{project_id}/brief", response_model=RequirementBrief)
def get_brief(project_id: str) -> RequirementBrief:
    service = get_project_service()
    try:
        return service.get_brief(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{project_id}/brief", response_model=RequirementBrief)
def update_brief(project_id: str, payload: BriefUpdateRequest) -> RequirementBrief:
    service = get_project_service()
    try:
        return service.update_brief(project_id, payload)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{project_id}/brief/confirm", response_model=BriefConfirmResponse)
def confirm_brief(project_id: str) -> BriefConfirmResponse:
    service = get_project_service()
    try:
        return service.confirm_brief(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{project_id}/outline/generate", response_model=OutlineArtifact)
def generate_outline(project_id: str) -> OutlineArtifact:
    service = get_project_service()
    try:
        return service.generate_outline(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{project_id}/outline", response_model=OutlineArtifact)
def get_outline(project_id: str) -> OutlineArtifact:
    service = get_project_service()
    try:
        return service.get_outline(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{project_id}/outline/reorder", response_model=OutlineArtifact)
def reorder_outline(
    project_id: str, payload: OutlineReorderRequest
) -> OutlineArtifact:
    service = get_project_service()
    try:
        return service.reorder_outline(project_id, payload)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{project_id}/slide-plan/generate", response_model=SlidePlanArtifact)
def generate_slide_plan(project_id: str) -> SlidePlanArtifact:
    service = get_project_service()
    try:
        return service.generate_slide_plan(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{project_id}/slide-plan", response_model=SlidePlanArtifact)
def get_slide_plan(project_id: str) -> SlidePlanArtifact:
    service = get_project_service()
    try:
        return service.get_slide_plan(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{project_id}/svg/generate", response_model=SvgSlideArtifact)
def generate_svg(project_id: str) -> SvgSlideArtifact:
    service = get_project_service()
    try:
        return service.generate_svg(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{project_id}/svg", response_model=SvgSlideArtifact)
def get_svg(project_id: str) -> SvgSlideArtifact:
    service = get_project_service()
    try:
        return service.get_svg(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
