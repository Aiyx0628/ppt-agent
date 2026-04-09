from functools import lru_cache
from uuid import uuid4
from datetime import UTC, datetime

from ppt_agent.config import get_settings
from ppt_agent.schemas.brief import BriefConfirmResponse, BriefQuestion, BriefUpdateRequest, RequirementBrief
from ppt_agent.schemas.outline import OutlineArtifact, OutlineReorderRequest, OutlineSlide
from ppt_agent.schemas.project import ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest
from ppt_agent.schemas.research import ResearchCitation, ResearchPack, ResearchTopic
from ppt_agent.services.storage_repository import ProjectNotFoundError, StorageRepository


class ProjectService:
    def __init__(self, repository: StorageRepository):
        self.repository = repository

    def list_projects(self) -> list[ProjectResponse]:
        return self.repository.list_projects()

    def create_project(self, payload: ProjectCreateRequest) -> ProjectResponse:
        now = datetime.now(UTC)
        project = ProjectResponse(
            id=f"proj_{uuid4().hex[:10]}",
            title=payload.title,
            topic=payload.topic,
            status="draft",
            config=payload.config,
            created_at=now,
            updated_at=now,
        )
        return self.repository.create_project(project)

    def get_project(self, project_id: str) -> ProjectResponse:
        return self.repository.get_project(project_id)

    def update_project(self, project_id: str, payload: ProjectUpdateRequest) -> ProjectResponse:
        return self.repository.update_project(project_id, payload)

    def delete_project(self, project_id: str) -> None:
        self.repository.delete_project(project_id)

    def generate_research(self, project_id: str) -> ResearchPack:
        project = self.get_project(project_id)
        pack = ResearchPack(
            project_id=project_id,
            version=1,
            summary=(
                f"Research framed for a {project.config.scenario} deck about "
                f"{project.topic}, tuned for {project.config.audience}."
            ),
            topics=[
                ResearchTopic(
                    name="Audience expectation",
                    summary="Clarify what decision-makers need to understand before they can approve the next step.",
                    cluster="Audience / Decision framing",
                    facts=[
                        f"{project.config.audience} needs fast clarity and decision confidence.",
                        "The story should surface the conclusion before the detail.",
                    ],
                    citations=[
                        ResearchCitation(
                            title="Executive communication patterns",
                            url="https://hbr.org/2024/01/how-to-communicate-clearly-with-executives",
                            snippet="Decision-makers prefer the recommendation first, supporting logic second.",
                        ),
                        ResearchCitation(
                            title="Presentation narrative guidance",
                            url="https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/the-pyramid-principle",
                            snippet="A strong narrative structure reduces decision latency and keeps discussions aligned.",
                        ),
                    ],
                ),
                ResearchTopic(
                    name="Story direction",
                    summary="Translate the topic into a slide-by-slide arc that feels concise, factual, and easy to act on.",
                    cluster="Narrative / Visual structure",
                    facts=[
                        f"The deck should stay aligned with a {project.config.style_pref} visual tone.",
                        "Each slide should keep one dominant message and one visual focal area.",
                    ],
                    citations=[
                        ResearchCitation(
                            title="Storytelling for product strategy decks",
                            url="https://a16z.com/good-product-strategy/",
                            snippet="Good strategy decks turn broad ambition into concrete tradeoffs and milestones.",
                        ),
                        ResearchCitation(
                            title="Designing information-dense slides",
                            url="https://informationisbeautiful.net/visualizations/what-makes-a-good-data-visualisation/",
                            snippet="Hierarchy, spacing, and one focal point per frame improve comprehension.",
                        ),
                    ],
                ),
            ],
        )
        stored = self.repository.save_artifact(
            project_id, "research", pack.model_dump(mode="json")
        )
        self.repository.update_project(
            project_id,
            ProjectUpdateRequest(status="briefing"),
        )
        return ResearchPack.model_validate(stored)

    def get_research(self, project_id: str) -> ResearchPack:
        stored = self.repository.load_artifact(project_id, "research")
        return ResearchPack.model_validate(stored)

    def generate_brief(self, project_id: str) -> RequirementBrief:
        project = self.get_project(project_id)
        try:
            research = self.get_research(project_id)
        except ProjectNotFoundError:
            research = self.generate_research(project_id)

        brief = RequirementBrief(
            project_id=project_id,
            version=1,
            goal=f"Build a {project.config.scenario} deck that lands the core point about {project.topic}.",
            audience=project.config.audience,
            tone=self._tone_from_style(project.config.style_pref),
            scenario=project.config.scenario,
            key_questions=[
                BriefQuestion(
                    id="goal",
                    prompt="What action should the audience take after the presentation?",
                    rationale="Sharpens the closing and the slide sequence.",
                    answer=f"Recognize why {project.topic} matters and support the next step.",
                ),
                BriefQuestion(
                    id="must_include",
                    prompt="What facts, examples, or numbers must appear no matter what?",
                    rationale="Prevents the deck from staying generic.",
                    answer=f"Examples, proof points, and a clear narrative for {project.topic}.",
                ),
                BriefQuestion(
                    id="risk",
                    prompt="What should the deck avoid saying or implying?",
                    rationale="Keeps the message appropriate for the audience.",
                    answer="Avoid jargon-heavy detours and unsupported claims.",
                ),
            ],
            must_include=[project.topic, project.config.scenario, "clear next step"],
            forbidden=["generic filler", "overlong text blocks"],
            research_summary=research.summary,
            confirmed=False,
        )
        stored = self.repository.save_artifact(
            project_id, "brief", brief.model_dump(mode="json")
        )
        return RequirementBrief.model_validate(stored)

    def get_brief(self, project_id: str) -> RequirementBrief:
        stored = self.repository.load_artifact(project_id, "brief")
        return RequirementBrief.model_validate(stored)

    def update_brief(self, project_id: str, payload: BriefUpdateRequest) -> RequirementBrief:
        current = self._get_or_generate_brief(project_id)
        updated = current.model_copy(
            update={
                "goal": payload.goal if payload.goal is not None else current.goal,
                "tone": payload.tone if payload.tone is not None else current.tone,
                "must_include": payload.must_include if payload.must_include is not None else current.must_include,
                "forbidden": payload.forbidden if payload.forbidden is not None else current.forbidden,
                "key_questions": payload.key_questions if payload.key_questions is not None else current.key_questions,
            }
        )
        stored = self.repository.save_artifact(
            project_id, "brief", updated.model_dump(mode="json")
        )
        return RequirementBrief.model_validate(stored)

    def confirm_brief(self, project_id: str) -> BriefConfirmResponse:
        current = self._get_or_generate_brief(project_id)
        confirmed = current.model_copy(update={"confirmed": True})
        self.repository.save_artifact(
            project_id, "brief", confirmed.model_dump(mode="json")
        )
        self.repository.update_project(
            project_id,
            ProjectUpdateRequest(status="brief_confirmed"),
        )
        return BriefConfirmResponse(project_id=project_id, confirmed=True)

    def generate_outline(self, project_id: str) -> OutlineArtifact:
        project = self.get_project(project_id)
        brief = self._get_or_generate_brief(project_id)
        slides = [
            OutlineSlide(
                slide_id=f"{project_id}_s{index+1}",
                order_no=index + 1,
                section=section,
                title=title,
                type=slide_type,
                key_message=message,
            )
            for index, (section, title, slide_type, message) in enumerate(
                [
                    ("Opening", project.title, "cover", f"{brief.goal}"),
                    ("Context", "Why This Matters Now", "argument", f"{project.topic} matters to {brief.audience}."),
                    ("Signal", "What We Learned", "key_metrics", brief.research_summary),
                    ("Shape", "Deck Narrative", "agenda", "A clear arc keeps the deck persuasive and fast to scan."),
                    ("Action", "Recommended Next Step", "closing", "End with one decision-ready ask."),
                ][: max(4, min(project.config.page_limit, 8))]
            )
        ]
        outline = OutlineArtifact(project_id=project_id, version=1, slides=slides)
        stored = self.repository.save_artifact(
            project_id, "outline", outline.model_dump(mode="json")
        )
        self.repository.update_project(
            project_id,
            ProjectUpdateRequest(status="outline_ready"),
        )
        return OutlineArtifact.model_validate(stored)

    def get_outline(self, project_id: str) -> OutlineArtifact:
        stored = self.repository.load_artifact(project_id, "outline")
        return OutlineArtifact.model_validate(stored)

    def reorder_outline(
        self, project_id: str, payload: OutlineReorderRequest
    ) -> OutlineArtifact:
        current = self.get_outline(project_id)
        existing = {slide.slide_id: slide for slide in current.slides}
        if set(payload.slide_ids) != set(existing):
            raise ProjectNotFoundError("Outline reorder payload does not match current slides.")

        slides = [
            existing[slide_id].model_copy(update={"order_no": order + 1})
            for order, slide_id in enumerate(payload.slide_ids)
        ]
        reordered = current.model_copy(update={"slides": slides})
        stored = self.repository.save_artifact(
            project_id, "outline", reordered.model_dump(mode="json")
        )
        return OutlineArtifact.model_validate(stored)

    def _get_or_generate_brief(self, project_id: str) -> RequirementBrief:
        try:
            stored = self.repository.load_artifact(project_id, "brief")
            return RequirementBrief.model_validate(stored)
        except ProjectNotFoundError:
            return self.generate_brief(project_id)

    def _tone_from_style(self, style_pref: str) -> str:
        mapping = {
            "business": "Concise, executive, decision-oriented.",
            "商务": "专业、克制、决策导向。",
            "科技": "清晰、前瞻、偏结构化。",
            "简洁": "克制、留白充分、重点突出。",
        }
        return mapping.get(style_pref, f"Polished and {style_pref}.")


@lru_cache
def get_project_service() -> ProjectService:
    settings = get_settings()
    return ProjectService(StorageRepository(settings.storage_root))
