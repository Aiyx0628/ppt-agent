from datetime import UTC, datetime
from functools import lru_cache
import re
from uuid import uuid4

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
        focus_points = self._extract_focus_points(project.topic)
        research_topics = [
            ResearchTopic(
                name="需求核心",
                summary="从用户输入中整理出的核心目标与展示范围。",
                cluster="Project brief",
                facts=[
                    f"项目标题：{project.title}",
                    f"核心需求：{self._clean_topic_text(project.topic)}",
                    f"目标页数：{project.config.page_limit} 页",
                ],
                citations=[],
            ),
            ResearchTopic(
                name="受众与场景",
                summary="展示对象、使用场景和风格偏好的真实约束。",
                cluster="Audience / Scenario",
                facts=[
                    f"受众：{project.config.audience}",
                    f"场景：{project.config.scenario}",
                    f"风格：{project.config.style_pref}",
                ],
                citations=[],
            ),
        ]

        for index, point in enumerate(focus_points[:6], start=1):
            research_topics.append(
                ResearchTopic(
                    name=self._clip_title(point, fallback=f"重点 {index}"),
                    summary=f"围绕“{point}”整理出的页面研究方向。",
                    cluster="Topic focus",
                    facts=[
                        point,
                        f"该主题需要服务于 {project.config.audience} 的信息接收方式。",
                        f"页面表达需保持 {project.config.style_pref} 风格与 {project.config.scenario} 语境一致。",
                    ],
                    citations=[],
                )
            )

        pack = ResearchPack(
            project_id=project_id,
            version=1,
            summary=(
                f"当前 research_pack 仅基于用户输入与项目配置整理，已抽取 {len(focus_points)} 个关注点，"
                "暂未接入外部联网检索与知识库引用。"
            ),
            topics=research_topics,
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
            goal=f"围绕“{project.title}”输出一套适用于{project.config.scenario}场景的演示文稿，并让{project.config.audience}快速理解重点。",
            audience=project.config.audience,
            tone=self._tone_from_style(project.config.style_pref),
            scenario=project.config.scenario,
            key_questions=[
                BriefQuestion(
                    id="goal",
                    prompt="这套内容最终希望观众形成什么判断或行动？",
                    rationale="决定收尾页和整套叙事的落点。",
                    answer=f"理解“{project.title}”的价值，并认可后续推进方向。",
                ),
                BriefQuestion(
                    id="must_include",
                    prompt="有哪些信息必须进入 PPT，不能被删掉？",
                    rationale="保证生成结果不会脱离原始需求。",
                    answer=self._clean_topic_text(project.topic),
                ),
                BriefQuestion(
                    id="risk",
                    prompt="这套内容要避免哪些表达方式？",
                    rationale="控制风格风险，避免出现不符合场景的语言。",
                    answer="避免无依据结论、无关铺垫和过度堆字。",
                ),
            ],
            must_include=[self._clean_topic_text(project.topic), project.config.scenario, project.config.audience],
            forbidden=["无依据扩写", "与主题无关的 filler", "整页长段落"],
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
        focus_points = self._extract_focus_points(project.topic)
        target_count = min(max(project.config.page_limit, 4), 16)

        plan: list[tuple[str, str, str, str]] = [
            ("封面", project.title, "cover", brief.goal),
            ("背景", "背景与目标", "context", self._clean_topic_text(project.topic)),
            ("总览", "核心信息总览", "summary", research_summary_from_brief(brief)),
        ]

        for index, point in enumerate(focus_points, start=1):
            plan.append(
                (
                    "重点",
                    self._clip_title(point, fallback=f"重点 {index}"),
                    "content",
                    point,
                )
            )

        plan.append(("结论", "结论与判断", "conclusion", f"围绕{project.title}收束核心判断。"))
        plan.append(("行动", "下一步建议", "closing", "给出可执行的下一步和落地建议。"))

        while len(plan) < target_count:
            slot = len(plan) - 2
            focus_point = focus_points[slot % len(focus_points)] if focus_points else self._clean_topic_text(project.topic)
            plan.insert(
                -2,
                (
                    "展开",
                    f"重点展开 {slot + 1}",
                    "content",
                    focus_point,
                ),
            )

        slides = [
            OutlineSlide(
                slide_id=f"{project_id}_s{index+1}",
                order_no=index + 1,
                section=section,
                title=title,
                type=slide_type,
                key_message=message,
            )
            for index, (section, title, slide_type, message) in enumerate(plan[:target_count])
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

    def _clean_topic_text(self, topic: str) -> str:
        cleaned_lines = [
            line.strip()
            for line in topic.splitlines()
            if line.strip() and not line.strip().startswith("附件：")
        ]
        return " ".join(cleaned_lines).strip() or topic.strip()

    def _extract_focus_points(self, topic: str) -> list[str]:
        cleaned = self._clean_topic_text(topic)
        parts = re.split(r"[。；;\n，,、]", cleaned)
        results: list[str] = []
        seen: set[str] = set()
        for part in parts:
            item = re.sub(r"\s+", " ", part).strip(" :-：")
            if len(item) < 2:
                continue
            if item in seen:
                continue
            seen.add(item)
            results.append(item)

        if not results and cleaned:
            results.append(cleaned)
        return results[:8]

    def _clip_title(self, text: str, fallback: str) -> str:
        compact = re.sub(r"\s+", " ", text).strip(" :-：")
        if not compact:
            return fallback
        return compact[:22]


def research_summary_from_brief(brief: RequirementBrief) -> str:
    return brief.research_summary or brief.goal


@lru_cache
def get_project_service() -> ProjectService:
    settings = get_settings()
    return ProjectService(StorageRepository(settings.storage_root))
