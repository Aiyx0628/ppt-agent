import json
from io import BytesIO
from datetime import UTC, datetime
from functools import lru_cache
import re
from pathlib import Path
from uuid import uuid4
from xml.sax.saxutils import escape
import zipfile
from xml.etree import ElementTree

from pydantic import ValidationError

from pypdf import PdfReader, PdfWriter

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None  # type: ignore[assignment,misc]

from ppt_agent.config import get_settings
from ppt_agent.schemas.brief import BriefConfirmResponse, BriefQuestion, BriefUpdateRequest, RequirementBrief
from ppt_agent.schemas.model import GenerateTextRequest
from ppt_agent.schemas.outline import OutlineArtifact, OutlineReorderRequest, OutlineSlide
from ppt_agent.schemas.project import ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest
from ppt_agent.schemas.research import ResearchPack, ResearchTopic
from ppt_agent.schemas.search import SearchArtifact, SearchPage
from ppt_agent.schemas.slide_plan import SlidePlanArtifact, SlidePlanBlock, SlidePlanPage, SlidePlanPageUpdateRequest
from ppt_agent.schemas.review import ReviewArtifact, ReviewIssue, ReviewPage
from ppt_agent.schemas.svg import SvgSlideArtifact, SvgSlidePage
from ppt_agent.services.model_router import ModelProviderError, get_model_router
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

    def create_project_from_intake(
        self,
        prompt: str,
        uploads: list[tuple[str, bytes]],
    ) -> ProjectResponse:
        prompt_text = prompt.strip()
        if len(prompt_text) < 3:
            raise ValueError("Prompt must be at least 3 characters.")

        files_text = self._compose_source_materials(uploads)
        payload = ProjectCreateRequest(
            title=self._derive_title_from_intake(prompt_text, uploads),
            topic=self._build_topic_from_intake(prompt_text, files_text, uploads),
            config=self._parse_project_config(prompt_text),
        )
        project = self.create_project(payload)
        for filename, content in uploads:
            self.repository.save_source_file(project.id, filename, content)
        return project

    def get_project(self, project_id: str) -> ProjectResponse:
        return self.repository.get_project(project_id)

    def update_project(self, project_id: str, payload: ProjectUpdateRequest) -> ProjectResponse:
        return self.repository.update_project(project_id, payload)

    def delete_project(self, project_id: str) -> None:
        self.repository.delete_project(project_id)

    def generate_research(self, project_id: str) -> ResearchPack:
        project = self.get_project(project_id)
        pack = self._generate_research_with_fallback(project)
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

    def generate_search_pages(self, project_id: str) -> SearchArtifact:
        try:
            research = self.get_research(project_id)
        except ProjectNotFoundError:
            research = self.generate_research(project_id)

        try:
            outline = self.get_outline(project_id)
        except ProjectNotFoundError:
            outline = self.generate_outline(project_id)

        pages = []
        for slide in outline.slides:
            related_topics = self._select_related_topics(slide, research.topics)
            pages.append(
                SearchPage(
                    slide_id=slide.slide_id,
                    order_no=slide.order_no,
                    title=slide.title,
                    section=slide.section,
                    key_message=slide.key_message,
                    summary=related_topics[0].summary if related_topics else research.summary,
                    facts=self._dedupe_strings(
                        [slide.key_message, *[fact for topic in related_topics for fact in topic.facts]]
                    )[:6],
                    citations=[
                        citation
                        for topic in related_topics
                        for citation in topic.citations
                    ][:6],
                )
            )
        artifact = SearchArtifact(project_id=project_id, version=1, pages=pages)
        stored = self.repository.save_artifact(
            project_id, "search_pages", artifact.model_dump(mode="json")
        )
        return SearchArtifact.model_validate(stored)

    def get_search_pages(self, project_id: str) -> SearchArtifact:
        stored = self.repository.load_artifact(project_id, "search_pages")
        return SearchArtifact.model_validate(stored)

    def generate_brief(self, project_id: str) -> RequirementBrief:
        project = self.get_project(project_id)
        try:
            research = self.get_research(project_id)
        except ProjectNotFoundError:
            research = self.generate_research(project_id)

        brief = self._generate_brief_with_fallback(project, research)
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
        outline = self._generate_outline_with_fallback(project, brief)
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

    def generate_slide_plan(self, project_id: str) -> SlidePlanArtifact:
        project = self.get_project(project_id)
        brief = self._get_or_generate_brief(project_id)
        outline = self.get_outline(project_id)
        slide_plan = self._generate_slide_plan_with_fallback(project, brief, outline)
        stored = self.repository.save_artifact(
            project_id, "slide_plan", slide_plan.model_dump(mode="json")
        )
        return SlidePlanArtifact.model_validate(stored)

    def get_slide_plan(self, project_id: str) -> SlidePlanArtifact:
        stored = self.repository.load_artifact(project_id, "slide_plan")
        return SlidePlanArtifact.model_validate(stored)

    def update_slide_plan_page(
        self,
        project_id: str,
        slide_id: str,
        payload: SlidePlanPageUpdateRequest,
    ) -> SlidePlanPage:
        current = self.get_slide_plan(project_id)
        page = next((p for p in current.pages if p.slide_id == slide_id), None)
        if page is None:
            raise ProjectNotFoundError(f"Slide {slide_id} not found in slide_plan.")

        updated_blocks = page.blocks
        if payload.blocks is not None:
            block_map = {b.block_id: b for b in payload.blocks}
            existing_ids = {b.block_id for b in page.blocks}
            unknown_ids = set(block_map.keys()) - existing_ids
            if unknown_ids:
                raise ProjectNotFoundError(f"Unknown block_ids: {', '.join(unknown_ids)}")
            updated_blocks = [
                block.model_copy(
                    update={
                        k: v
                        for k, v in {
                            "title": block_map[block.block_id].title if block.block_id in block_map else None,
                            "content": block_map[block.block_id].content if block.block_id in block_map else None,
                            "emphasis": block_map[block.block_id].emphasis if block.block_id in block_map else None,
                        }.items()
                        if v is not None
                    }
                )
                for block in page.blocks
            ]

        updated_page = page.model_copy(
            update={
                k: v
                for k, v in {
                    "title": payload.title,
                    "core_message": payload.core_message,
                    "visual_focus": payload.visual_focus,
                    "blocks": updated_blocks,
                }.items()
                if v is not None
            }
        )
        updated_pages = [
            updated_page if p.slide_id == slide_id else p for p in current.pages
        ]
        updated_artifact = current.model_copy(update={"pages": updated_pages})
        self.repository.save_artifact(
            project_id, "slide_plan", updated_artifact.model_dump(mode="json")
        )
        return updated_page

    def generate_svg(self, project_id: str) -> SvgSlideArtifact:
        project = self.get_project(project_id)
        slide_plan = self.get_slide_plan(project_id)
        svg_artifact = self._generate_svg_with_fallback(project, slide_plan)
        stored = self.repository.save_artifact(
            project_id, "svg_slide", svg_artifact.model_dump(mode="json")
        )
        return SvgSlideArtifact.model_validate(stored)

    def get_svg(self, project_id: str) -> SvgSlideArtifact:
        stored = self.repository.load_artifact(project_id, "svg_slide")
        return SvgSlideArtifact.model_validate(stored)

    def regenerate_svg_page(self, project_id: str, slide_id: str) -> SvgSlidePage:
        project = self.get_project(project_id)
        slide_plan = self.get_slide_plan(project_id)
        plan_page = next((p for p in slide_plan.pages if p.slide_id == slide_id), None)
        if plan_page is None:
            raise ProjectNotFoundError(f"Slide {slide_id} not found in slide_plan.")

        new_svg_page = self._regenerate_single_svg_page(project, plan_page)

        current_svg = self.get_svg(project_id)
        updated_pages = [
            new_svg_page if p.slide_id == slide_id else p for p in current_svg.pages
        ]
        updated_artifact = current_svg.model_copy(update={"pages": updated_pages})
        self.repository.save_artifact(
            project_id, "svg_slide", updated_artifact.model_dump(mode="json")
        )
        return new_svg_page

    def export_svg_zip(self, project_id: str) -> bytes:
        svg_artifact = self.get_svg(project_id)
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for page in sorted(svg_artifact.pages, key=lambda p: p.order_no):
                filename = f"slide_{page.order_no:02d}.svg"
                zf.writestr(filename, page.svg.encode("utf-8"))
        return buffer.getvalue()

    def export_pdf(self, project_id: str) -> bytes:
        import cairosvg  # lazy: requires system cairo library (DYLD_LIBRARY_PATH on macOS)
        svg_artifact = self.get_svg(project_id)
        writer = PdfWriter()
        for page in sorted(svg_artifact.pages, key=lambda p: p.order_no):
            single_pdf = cairosvg.svg2pdf(bytestring=page.svg.encode("utf-8"))
            reader = PdfReader(BytesIO(single_pdf))
            for pdf_page in reader.pages:
                writer.add_page(pdf_page)

        output = BytesIO()
        writer.write(output)
        return output.getvalue()

    def run_review(self, project_id: str) -> ReviewArtifact:
        svg_artifact = self.get_svg(project_id)
        pages = [self._review_svg_page(page) for page in svg_artifact.pages]
        artifact = ReviewArtifact(project_id=project_id, version=1, pages=pages)
        self.repository.save_artifact(
            project_id, "review", artifact.model_dump(mode="json")
        )
        return artifact

    def get_review(self, project_id: str) -> ReviewArtifact:
        stored = self.repository.load_artifact(project_id, "review")
        return ReviewArtifact.model_validate(stored)

    def _review_svg_page(self, page: SvgSlidePage) -> ReviewPage:
        issues: list[ReviewIssue] = []

        # 检查 1：SVG 结构合法性
        try:
            root = ElementTree.fromstring(page.svg)
        except ElementTree.ParseError as exc:
            issues.append(ReviewIssue(
                code="invalid_xml",
                severity="error",
                detail=f"SVG 无法解析：{exc}",
            ))
            return ReviewPage(
                slide_id=page.slide_id,
                order_no=page.order_no,
                issues=issues,
                passed=False,
            )

        # 检查 2：viewBox
        has_viewbox = "viewBox" in (root.attrib or {})
        has_size = "width" in (root.attrib or {}) and "height" in (root.attrib or {})
        if not has_viewbox and not has_size:
            issues.append(ReviewIssue(
                code="missing_viewbox",
                severity="warning",
                detail="SVG 缺少 viewBox 或 width/height，可能导致缩放异常。",
            ))

        # 检查 3：是否有文字内容
        all_text = " ".join(
            (el.text or "") + (el.tail or "")
            for el in root.iter()
            if el.tag in {
                "{http://www.w3.org/2000/svg}text",
                "{http://www.w3.org/2000/svg}tspan",
            }
        ).strip()
        if not all_text:
            issues.append(ReviewIssue(
                code="no_text_content",
                severity="warning",
                detail="SVG 中未检测到文字内容，可能为空白页。",
            ))

        # 检查 4：文字总长度是否超出阈值
        if len(all_text) > 800:
            issues.append(ReviewIssue(
                code="text_overflow_risk",
                severity="warning",
                detail=f"SVG 文字总长度 {len(all_text)} 字符，超过 800 字阈值，存在溢出风险。",
            ))

        return ReviewPage(
            slide_id=page.slide_id,
            order_no=page.order_no,
            issues=issues,
            passed=len([i for i in issues if i.severity == "error"]) == 0,
        )

    def _get_or_generate_brief(self, project_id: str) -> RequirementBrief:
        try:
            stored = self.repository.load_artifact(project_id, "brief")
            return RequirementBrief.model_validate(stored)
        except ProjectNotFoundError:
            return self.generate_brief(project_id)

    def _fetch_tavily_results(
        self,
        project: ProjectResponse,
        api_key: str | None,
    ) -> list[dict[str, str]]:
        if not api_key or TavilyClient is None:
            return []
        try:
            keywords = self._extract_search_keywords(project)
            client = TavilyClient(api_key=api_key)
            results: list[dict[str, str]] = []
            for kw in keywords[:3]:
                resp = client.search(kw, max_results=3, search_depth="basic")
                for item in resp.get("results", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                    })
            return results[:9]
        except Exception:
            return []

    def _extract_search_keywords(self, project: ProjectResponse) -> list[str]:
        tokens = self._tokenize(f"{project.title} {project.config.scenario} {project.config.audience}")
        return tokens[:3] if tokens else [project.title]

    def _generate_research_with_fallback(self, project: ProjectResponse) -> ResearchPack:
        settings = get_settings()
        search_results = self._fetch_tavily_results(project, api_key=settings.tavily_api_key)
        try:
            return self._generate_research_with_model(project, search_results=search_results)
        except (ModelProviderError, ValidationError, ValueError, json.JSONDecodeError):
            return self._generate_research_fallback(project)

    def _generate_brief_with_fallback(
        self,
        project: ProjectResponse,
        research: ResearchPack,
    ) -> RequirementBrief:
        try:
            return self._generate_brief_with_model(project, research)
        except (ModelProviderError, ValidationError, ValueError, json.JSONDecodeError):
            return self._generate_brief_fallback(project, research)

    def _generate_outline_with_fallback(
        self,
        project: ProjectResponse,
        brief: RequirementBrief,
    ) -> OutlineArtifact:
        try:
            return self._generate_outline_with_model(project, brief)
        except (ModelProviderError, ValidationError, ValueError, json.JSONDecodeError):
            return self._generate_outline_fallback(project, brief)

    def _generate_slide_plan_with_fallback(
        self,
        project: ProjectResponse,
        brief: RequirementBrief,
        outline: OutlineArtifact,
    ) -> SlidePlanArtifact:
        try:
            return self._generate_slide_plan_with_model(project, brief, outline)
        except (ModelProviderError, ValidationError, ValueError, json.JSONDecodeError):
            return self._generate_slide_plan_fallback(project, brief, outline)

    def _regenerate_single_svg_page(
        self,
        project: ProjectResponse,
        plan_page: SlidePlanPage,
    ) -> SvgSlidePage:
        try:
            return self._regenerate_single_svg_page_with_model(project, plan_page)
        except (ModelProviderError, ValidationError, ValueError, json.JSONDecodeError):
            return SvgSlidePage(
                slide_id=plan_page.slide_id,
                order_no=plan_page.order_no,
                title=plan_page.title,
                svg=self._render_svg_page(project, plan_page),
            )

    def _regenerate_single_svg_page_with_model(
        self,
        project: ProjectResponse,
        plan_page: SlidePlanPage,
    ) -> SvgSlidePage:
        block_lines = "\n".join(
            f"  - [{b.kind}] {b.title}：{b.content}（强调={b.emphasis}）"
            for b in plan_page.blocks
        )
        prompt = f"""请根据以下单页策划生成整页 SVG。

项目标题：{project.title}
受众：{project.config.audience}
场景：{project.config.scenario}
风格：{project.config.style_pref}

页面策划：
- 第{plan_page.order_no}页 | {plan_page.title} | {plan_page.core_message} | 布局={plan_page.suggested_layout}
块内容：
{block_lines}

输出 JSON，格式如下：
{{
  "title": "string",
  "svg": "<svg ...>...</svg>"
}}

要求：
1. svg 必须是完整合法的 SVG 字符串。
2. 画布统一使用 viewBox="0 0 1280 720"。
3. 风格偏向简洁、结构化、适合企业汇报。""".strip()

        response = get_model_router().generate_text(
            GenerateTextRequest(
                prompt=prompt,
                system_instruction="你是 SVG 幻灯片设计助手。请只输出 JSON。不要输出 markdown，不要解释。",
                max_output_tokens=2048,
                temperature=0.4,
            )
        )
        data = self._load_json_object(response.text)
        return SvgSlidePage(
            slide_id=plan_page.slide_id,
            order_no=plan_page.order_no,
            title=data.get("title", plan_page.title),
            svg=data["svg"],
        )

    def _generate_svg_with_fallback(
        self,
        project: ProjectResponse,
        slide_plan: SlidePlanArtifact,
    ) -> SvgSlideArtifact:
        try:
            return self._generate_svg_with_model(project, slide_plan)
        except (ModelProviderError, ValidationError, ValueError, json.JSONDecodeError):
            return self._generate_svg_fallback(project, slide_plan)

    def _generate_research_with_model(
        self,
        project: ProjectResponse,
        search_results: list[dict[str, str]] | None = None,
    ) -> ResearchPack:
        response = get_model_router().generate_text(
            GenerateTextRequest(
                prompt=self._build_research_prompt(project, search_results=search_results or []),
                system_instruction=(
                    "你是 PPT 调研助理。请只输出 JSON。不要输出 markdown，不要解释。"
                ),
                max_output_tokens=1800,
                temperature=0.4,
            )
        )
        data = self._load_json_object(response.text)
        payload = {
            "project_id": project.id,
            "version": 1,
            "summary": data["summary"],
            "topics": data["topics"],
        }
        return ResearchPack.model_validate(payload)

    def _generate_brief_with_model(
        self,
        project: ProjectResponse,
        research: ResearchPack,
    ) -> RequirementBrief:
        response = get_model_router().generate_text(
            GenerateTextRequest(
                prompt=self._build_brief_prompt(project, research),
                system_instruction=(
                    "你是 PPT 需求顾问。请只输出 JSON。不要输出 markdown，不要解释。"
                ),
                max_output_tokens=1800,
                temperature=0.5,
            )
        )
        data = self._load_json_object(response.text)
        payload = {
            "project_id": project.id,
            "version": 1,
            "goal": data["goal"],
            "audience": project.config.audience,
            "tone": data["tone"],
            "scenario": project.config.scenario,
            "key_questions": data["key_questions"],
            "must_include": data["must_include"],
            "forbidden": data["forbidden"],
            "research_summary": research.summary,
            "confirmed": False,
        }
        return RequirementBrief.model_validate(payload)

    def _generate_outline_with_model(
        self,
        project: ProjectResponse,
        brief: RequirementBrief,
    ) -> OutlineArtifact:
        response = get_model_router().generate_text(
            GenerateTextRequest(
                prompt=self._build_outline_prompt(project, brief),
                system_instruction=(
                    "你是 PPT 大纲策划专家。请只输出 JSON。不要输出 markdown，不要解释。"
                ),
                max_output_tokens=2200,
                temperature=0.5,
            )
        )
        data = self._load_json_object(response.text)
        slides = [
            OutlineSlide(
                slide_id=f"{project.id}_s{index + 1}",
                order_no=index + 1,
                section=item["section"],
                title=item["title"],
                type=item["type"],
                key_message=item["key_message"],
            )
            for index, item in enumerate(data["slides"][: self._target_slide_count(project)])
        ]
        return OutlineArtifact(project_id=project.id, version=1, slides=slides)

    def _generate_slide_plan_with_model(
        self,
        project: ProjectResponse,
        brief: RequirementBrief,
        outline: OutlineArtifact,
    ) -> SlidePlanArtifact:
        response = get_model_router().generate_text(
            GenerateTextRequest(
                prompt=self._build_slide_plan_prompt(project, brief, outline),
                system_instruction=(
                    "你是 PPT 单页策划专家。请只输出 JSON。不要输出 markdown，不要解释。"
                ),
                max_output_tokens=3200,
                temperature=0.5,
            )
        )
        data = self._load_json_object(response.text)
        pages = [
            SlidePlanPage.model_validate(
                {
                    "slide_id": slide.slide_id,
                    "order_no": slide.order_no,
                    **page,
                }
            )
            for slide, page in zip(outline.slides, data["pages"], strict=False)
        ]
        if len(pages) != len(outline.slides):
            raise ValueError("Slide plan page count does not match outline.")
        return SlidePlanArtifact(project_id=project.id, version=1, pages=pages)

    def _generate_svg_with_model(
        self,
        project: ProjectResponse,
        slide_plan: SlidePlanArtifact,
    ) -> SvgSlideArtifact:
        response = get_model_router().generate_text(
            GenerateTextRequest(
                prompt=self._build_svg_prompt(project, slide_plan),
                system_instruction=(
                    "你是 SVG 幻灯片设计助手。请只输出 JSON。不要输出 markdown，不要解释。"
                ),
                max_output_tokens=4096,
                temperature=0.4,
            )
        )
        data = self._load_json_object(response.text)
        pages = [
            SvgSlidePage.model_validate(
                {
                    "slide_id": plan_page.slide_id,
                    "order_no": plan_page.order_no,
                    **page,
                }
            )
            for plan_page, page in zip(slide_plan.pages, data["pages"], strict=False)
        ]
        if len(pages) != len(slide_plan.pages):
            raise ValueError("SVG page count does not match slide plan.")
        return SvgSlideArtifact(project_id=project.id, version=1, pages=pages)

    def _generate_research_fallback(self, project: ProjectResponse) -> ResearchPack:
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

        return ResearchPack(
            project_id=project.id,
            version=1,
            summary=(
                f"当前 research_pack 仅基于用户输入与项目配置整理，已抽取 {len(focus_points)} 个关注点，"
                "暂未接入外部联网检索与知识库引用。"
            ),
            topics=research_topics,
        )

    def _generate_brief_fallback(
        self,
        project: ProjectResponse,
        research: ResearchPack,
    ) -> RequirementBrief:
        return RequirementBrief(
            project_id=project.id,
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

    def _generate_outline_fallback(
        self,
        project: ProjectResponse,
        brief: RequirementBrief,
    ) -> OutlineArtifact:
        focus_points = self._extract_focus_points(project.topic)
        target_count = self._target_slide_count(project)

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
                slide_id=f"{project.id}_s{index + 1}",
                order_no=index + 1,
                section=section,
                title=title,
                type=slide_type,
                key_message=message,
            )
            for index, (section, title, slide_type, message) in enumerate(plan[:target_count])
        ]
        return OutlineArtifact(project_id=project.id, version=1, slides=slides)

    def _generate_slide_plan_fallback(
        self,
        project: ProjectResponse,
        brief: RequirementBrief,
        outline: OutlineArtifact,
    ) -> SlidePlanArtifact:
        pages = [
            SlidePlanPage(
                slide_id=slide.slide_id,
                order_no=slide.order_no,
                title=slide.title,
                narrative_role=self._map_narrative_role(slide.type),
                core_message=slide.key_message,
                visual_focus=self._infer_visual_focus(slide),
                suggested_layout=self._infer_layout(slide),
                design_notes=[
                    f"受众保持为 {project.config.audience}。",
                    f"页面语气保持 {brief.tone}",
                    "单页只突出一个核心结论。",
                ],
                blocks=[
                    SlidePlanBlock(
                        block_id=f"{slide.slide_id}_headline",
                        kind="headline",
                        title="核心标题",
                        content=slide.title,
                        words_budget=18,
                        emphasis="high",
                    ),
                    SlidePlanBlock(
                        block_id=f"{slide.slide_id}_message",
                        kind="summary",
                        title="核心结论",
                        content=slide.key_message,
                        words_budget=40,
                        emphasis="high",
                    ),
                    SlidePlanBlock(
                        block_id=f"{slide.slide_id}_support",
                        kind="bullets",
                        title="支撑信息",
                        content=self._clean_topic_text(project.topic),
                        words_budget=90,
                        emphasis="medium",
                    ),
                ],
            )
            for slide in outline.slides
        ]
        return SlidePlanArtifact(project_id=project.id, version=1, pages=pages)

    def _generate_svg_fallback(
        self,
        project: ProjectResponse,
        slide_plan: SlidePlanArtifact,
    ) -> SvgSlideArtifact:
        pages = [
            SvgSlidePage(
                slide_id=page.slide_id,
                order_no=page.order_no,
                title=page.title,
                svg=self._render_svg_page(project, page),
            )
            for page in slide_plan.pages
        ]
        return SvgSlideArtifact(project_id=project.id, version=1, pages=pages)

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

    def _dedupe_strings(self, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))

    def _tokenize(self, text: str) -> list[str]:
        return [
            token
            for token in self._dedupe_strings(
                re.split(r"[\s，,。；;：:、()（）/]+", text)
            )
            if len(token) >= 2
        ]

    def _select_related_topics(
        self,
        slide: OutlineSlide,
        topics: list[ResearchTopic],
    ) -> list[ResearchTopic]:
        if not topics:
            return []

        tokens = self._tokenize(f"{slide.title} {slide.key_message} {slide.section}")
        scored = sorted(
            (
                (
                    sum(
                        1
                        for token in tokens
                        if token in f"{topic.name} {topic.summary} {' '.join(topic.facts)}"
                    ),
                    index,
                    topic,
                )
                for index, topic in enumerate(topics)
            ),
            key=lambda item: (-item[0], item[1]),
        )
        if scored[0][0] == 0:
            return [topics[(slide.order_no - 1) % len(topics)]]
        return [topic for score, _, topic in scored if score > 0][:2]

    def _clip_title(self, text: str, fallback: str) -> str:
        compact = re.sub(r"\s+", " ", text).strip(" :-：")
        if not compact:
            return fallback
        return compact[:22]

    def _target_slide_count(self, project: ProjectResponse) -> int:
        return min(max(project.config.page_limit, 4), 16)

    def _derive_title_from_intake(
        self,
        prompt: str,
        uploads: list[tuple[str, bytes]],
    ) -> str:
        if uploads:
            stem = Path(uploads[0][0]).stem.strip()
            if stem:
                return stem[:48]
        first_line = prompt.splitlines()[0].strip()
        if first_line:
            return first_line[:48]
        return "DeckFlow 项目"

    def _parse_project_config(self, prompt: str):
        from ppt_agent.schemas.project import ProjectConfigPayload

        page_match = re.search(r"(\d{1,2})\s*页", prompt)
        page_limit = int(page_match.group(1)) if page_match else 14
        style_pref = (
            "商务"
            if "商务" in prompt
            else "简洁"
            if "简洁" in prompt
            else "科技"
        )
        scenario = (
            "培训"
            if "培训" in prompt
            else "路演"
            if "路演" in prompt
            else "总结"
            if "总结" in prompt
            else "汇报"
        )
        audience = self._extract_audience(prompt)
        return ProjectConfigPayload(
            scenario=scenario,
            audience=audience,
            style_pref=style_pref,
            page_limit=min(max(page_limit, 4), 20),
            research_enabled=True,
            narration_enabled=False,
        )

    def _extract_audience(self, prompt: str) -> str:
        audience_match = re.search(r"适合([^，。；\n]{2,20})", prompt)
        if audience_match:
            return audience_match.group(1).strip()
        if "老板" in prompt:
            return "老板 / 管理层"
        if "团队" in prompt:
            return "团队成员 / 项目负责人"
        return "产品负责人 / 决策层"

    def _build_topic_from_intake(
        self,
        prompt: str,
        source_texts: list[tuple[str, str]],
        uploads: list[tuple[str, bytes]],
    ) -> str:
        sections = [prompt]
        if uploads:
            sections.append(
                "附件：" + "、".join(filename for filename, _ in uploads)
            )
        for filename, text in source_texts:
            sections.append(f"资料 {filename}：{self._truncate(text, 3600)}")
        return "\n\n".join(sections)

    def _compose_source_materials(
        self,
        uploads: list[tuple[str, bytes]],
    ) -> list[tuple[str, str]]:
        materials: list[tuple[str, str]] = []
        for filename, content in uploads:
            extracted = self._extract_text_from_upload(filename, content)
            if extracted:
                materials.append((filename, extracted))
        return materials

    def _extract_text_from_upload(self, filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix in {".md", ".txt", ".text"}:
            return self._decode_text_bytes(content)
        if suffix == ".docx":
            return self._extract_docx_text(content)
        return ""

    def _decode_text_bytes(self, content: bytes) -> str:
        for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
            try:
                return content.decode(encoding).strip()
            except UnicodeDecodeError:
                continue
        return ""

    def _extract_docx_text(self, content: bytes) -> str:
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                document_xml = archive.read("word/document.xml")
        except (KeyError, zipfile.BadZipFile):
            return ""

        root = ElementTree.fromstring(document_xml)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        texts = [
            node.text.strip()
            for node in root.findall(".//w:t", namespace)
            if node.text and node.text.strip()
        ]
        return re.sub(r"\s+", " ", " ".join(texts)).strip()

    def _load_json_object(self, raw_text: str) -> dict:
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return json.loads(text)

    def _build_research_prompt(
        self,
        project: ProjectResponse,
        search_results: list[dict[str, str]] | None = None,
    ) -> str:
        search_section = ""
        if search_results:
            lines = "\n".join(
                f"- [{item['title']}]({item['url']}): {item['content'][:200]}"
                for item in search_results
            )
            search_section = f"\n\n以下是来自外部搜索的参考资料（请优先引用）：\n{lines}"
        return f"""
请根据以下项目信息生成 research_pack。

项目标题：{project.title}
项目需求：{self._clean_topic_text(project.topic)}
受众：{project.config.audience}
场景：{project.config.scenario}
风格：{project.config.style_pref}
页数：{project.config.page_limit}

输出 JSON，格式如下：
{{
  "summary": "string",
  "topics": [
    {{
      "name": "string",
      "summary": "string",
      "cluster": "string",
      "facts": ["string"],
      "citations": [
        {{"title": "string", "url": "string", "snippet": "string"}}
      ]
    }}
  ]
}}

要求：
1. 如果没有真实联网来源，citations 返回空数组。
2. topics 数量控制在 3 到 6 个。
3. facts 必须来自用户输入和项目配置，不要编造数字。{search_section}
""".strip()

    def _build_brief_prompt(self, project: ProjectResponse, research: ResearchPack) -> str:
        topic_lines = "\n".join(
            f"- {topic.name}: {topic.summary}"
            for topic in research.topics[:6]
        )
        return f"""
请根据项目信息和 research 结果生成需求 brief。

项目标题：{project.title}
原始需求：{self._clean_topic_text(project.topic)}
受众：{project.config.audience}
场景：{project.config.scenario}
风格：{project.config.style_pref}
研究摘要：{research.summary}
研究主题：
{topic_lines}

输出 JSON，格式如下：
{{
  "goal": "string",
  "tone": "string",
  "key_questions": [
    {{
      "id": "goal",
      "prompt": "string",
      "rationale": "string",
      "answer": "string"
    }}
  ],
  "must_include": ["string"],
  "forbidden": ["string"]
}}

要求：
1. key_questions 输出 3 个。
2. 必须使用中文。
3. 不要脱离原始需求扩写无依据结论。
""".strip()

    def _build_outline_prompt(self, project: ProjectResponse, brief: RequirementBrief) -> str:
        question_lines = "\n".join(
            f"- {question.prompt} / {question.answer}"
            for question in brief.key_questions
        )
        return f"""
请根据项目与 brief 生成 PPT 大纲。

项目标题：{project.title}
原始需求：{self._clean_topic_text(project.topic)}
目标：{brief.goal}
受众：{brief.audience}
场景：{brief.scenario}
语气：{brief.tone}
必须包含：{", ".join(brief.must_include)}
避免内容：{", ".join(brief.forbidden)}
补充问答：
{question_lines}
目标页数：{self._target_slide_count(project)}

输出 JSON，格式如下：
{{
  "slides": [
    {{
      "section": "string",
      "title": "string",
      "type": "cover|context|summary|content|conclusion|closing",
      "key_message": "string"
    }}
  ]
}}

要求：
1. slides 数量必须等于目标页数。
2. 每页只保留一个核心结论。
3. 标题简洁，避免模板化空话。
""".strip()

    def _build_slide_plan_prompt(
        self,
        project: ProjectResponse,
        brief: RequirementBrief,
        outline: OutlineArtifact,
    ) -> str:
        outline_lines = "\n".join(
            f"- 第{slide.order_no}页 | {slide.title} | {slide.type} | {slide.key_message}"
            for slide in outline.slides
        )
        return f"""
请根据项目 brief 和 outline，输出逐页 slide_plan。

项目标题：{project.title}
受众：{brief.audience}
场景：{brief.scenario}
语气：{brief.tone}
目标：{brief.goal}
必须包含：{", ".join(brief.must_include)}
避免内容：{", ".join(brief.forbidden)}

大纲：
{outline_lines}

输出 JSON，格式如下：
{{
  "pages": [
    {{
      "title": "string",
      "narrative_role": "string",
      "core_message": "string",
      "visual_focus": "string",
      "suggested_layout": "string",
      "design_notes": ["string"],
      "blocks": [
        {{
          "block_id": "string",
          "kind": "string",
          "title": "string",
          "content": "string",
          "words_budget": 40,
          "emphasis": "high|medium|low"
        }}
      ]
    }}
  ]
}}

要求：
1. pages 数量必须与大纲页数完全一致。
2. 每页 blocks 数量 3 到 5 个。
3. 设计说明要能直接服务于后续 SVG 生成。
4. 使用中文。
""".strip()

    def _build_svg_prompt(
        self,
        project: ProjectResponse,
        slide_plan: SlidePlanArtifact,
    ) -> str:
        page_lines = "\n".join(
            f"- 第{page.order_no}页 | {page.title} | {page.core_message} | 布局={page.suggested_layout}"
            for page in slide_plan.pages
        )
        return f"""
请根据 slide_plan 为每一页生成整页 SVG。

项目标题：{project.title}
受众：{project.config.audience}
场景：{project.config.scenario}
风格：{project.config.style_pref}

页面策划：
{page_lines}

输出 JSON，格式如下：
{{
  "pages": [
    {{
      "title": "string",
      "svg": "<svg ...>...</svg>"
    }}
  ]
}}

要求：
1. 每页 svg 都必须是完整合法的 SVG 字符串。
2. 画布统一使用 viewBox="0 0 1280 720"。
3. 风格偏向简洁、结构化、适合企业汇报。
4. pages 数量必须与 slide_plan 一致。
""".strip()

    def _map_narrative_role(self, slide_type: str) -> str:
        mapping = {
            "cover": "开场建立主题",
            "context": "说明背景与问题",
            "summary": "提炼关键信息",
            "content": "展开核心论点",
            "conclusion": "收束核心判断",
            "closing": "给出下一步建议",
        }
        return mapping.get(slide_type, "展开核心内容")

    def _infer_visual_focus(self, slide: OutlineSlide) -> str:
        mapping = {
            "cover": "标题与副标题",
            "context": "背景信息与问题定义",
            "summary": "一屏总结与重点摘录",
            "content": "单个核心结论及支撑块",
            "conclusion": "结论卡片与判断语句",
            "closing": "行动建议与落地步骤",
        }
        return mapping.get(slide.type, "核心结论卡片")

    def _infer_layout(self, slide: OutlineSlide) -> str:
        mapping = {
            "cover": "标题居中 + 副标题 + 轻背景装饰",
            "context": "左标题右说明的双栏布局",
            "summary": "顶部标题 + 下方 2x2 信息卡片",
            "content": "顶部标题 + 主卡片 + 辅助说明卡片",
            "conclusion": "大结论卡片 + supporting bullets",
            "closing": "步骤卡片 + CTA 区域",
        }
        return mapping.get(slide.type, "顶部标题 + 内容卡片网格")

    def _render_svg_page(self, project: ProjectResponse, page: SlidePlanPage) -> str:
        blocks = page.blocks[:4]
        rendered_blocks: list[str] = []
        positions = [
            (70, 190, 540, 190),
            (670, 190, 540, 190),
            (70, 410, 540, 190),
            (670, 410, 540, 190),
        ]
        for block, (x, y, width, height) in zip(blocks, positions, strict=False):
            rendered_blocks.append(
                f"""
                <g>
                  <rect x="{x}" y="{y}" width="{width}" height="{height}" rx="26" fill="#FFFFFF" stroke="#D8DFEB"/>
                  <text x="{x + 28}" y="{y + 42}" fill="#1F293D" font-size="24" font-weight="700">{escape(block.title)}</text>
                  <text x="{x + 28}" y="{y + 82}" fill="#6F7F9A" font-size="18">{escape(self._truncate(block.content, 88))}</text>
                  <text x="{x + 28}" y="{y + height - 24}" fill="#2D6CF6" font-size="16">{escape(block.kind)} · {escape(block.emphasis)}</text>
                </g>
                """.strip()
            )

        return f"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <rect width="1280" height="720" fill="#EEF3FB"/>
  <rect x="34" y="34" width="1212" height="652" rx="34" fill="#F8FAFD" stroke="#D8DFEB"/>
  <rect x="58" y="58" width="1164" height="604" rx="30" fill="#FFFFFF"/>
  <rect x="92" y="94" width="6" height="60" rx="3" fill="#2D6CF6"/>
  <text x="116" y="126" fill="#1F293D" font-size="34" font-weight="700">{escape(page.title)}</text>
  <text x="116" y="162" fill="#7D8AA5" font-size="18">{escape(page.core_message)}</text>
  <text x="1080" y="126" fill="#97A5BF" font-size="16">Page {page.order_no:02d}</text>
  <text x="1080" y="154" fill="#97A5BF" font-size="14">{escape(project.config.style_pref)} / {escape(page.suggested_layout)}</text>
  {"".join(rendered_blocks)}
</svg>
        """.strip()

    def _truncate(self, text: str, limit: int) -> str:
        clean = re.sub(r"\s+", " ", text).strip()
        if len(clean) <= limit:
            return clean
        return f"{clean[: limit - 1]}…"


def research_summary_from_brief(brief: RequirementBrief) -> str:
    return brief.research_summary or brief.goal


@lru_cache
def get_project_service() -> ProjectService:
    settings = get_settings()
    return ProjectService(StorageRepository(settings.storage_root))
