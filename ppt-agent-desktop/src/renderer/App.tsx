import { startTransition, useEffect, useMemo, useRef, useState } from "react";

import { api } from "./services/api";
import type {
  HealthResponse,
  OutlineArtifact,
  OutlineSlide,
  Project,
  RequirementBrief,
  ResearchPack,
  ReviewArtifact,
  ReviewPage,
  SearchArtifact,
  SearchPage,
  SlidePlanArtifact,
  SlidePlanPage,
  SvgSlideArtifact,
  SvgSlidePage,
} from "./types";

type HealthState =
  | { status: "loading" }
  | { status: "ready"; payload: HealthResponse }
  | { status: "error"; message: string };

type StageView = "search" | "draft" | "design";
type PageView = "intake" | "editor";

type WorkspaceState = {
  projects: Project[];
  selectedProjectId: string | null;
  brief: RequirementBrief | null;
  research: ResearchPack | null;
  outline: OutlineArtifact | null;
  searchPages: SearchArtifact | null;
  slidePlan: SlidePlanArtifact | null;
  svgArtifact: SvgSlideArtifact | null;
  selectedSlideId: string | null;
  isBusy: boolean;
  draftEditState: {
    title: string;
    core_message: string;
    visual_focus: string;
    blocks: Array<{ block_id: string; title: string; content: string; emphasis: string }>;
  } | null;
  isSaving: boolean;
  regeneratingSlideId: string | null;
  reviewArtifact: ReviewArtifact | null;
  isReviewing: boolean;
  error: string | null;
};

type SlideReference = {
  slide_id: string;
  order_no: number;
  title: string;
};

type ChatMessage = {
  id: string;
  role: "ai" | "user";
  text: string;
  time: string;
};

const DEFAULT_TITLE = "全链路 LLMOps：覆盖开发、调试至监控的生命周期";
const DEFAULT_PROMPT =
  "请基于我上传的资料，生成一套 14 页、科技感、适合团队汇报的 PPT，重点突出开发、调试、监控、闭环优化和生态集成。";

const stageLabels: Record<StageView, string> = {
  search: "搜索",
  draft: "初稿",
  design: "设计稿",
};

export function App() {
  const [health, setHealth] = useState<HealthState>({ status: "loading" });
  const [pageView, setPageView] = useState<PageView>("intake");
  const [stage, setStage] = useState<StageView>("search");
  const [workspace, setWorkspace] = useState<WorkspaceState>({
    projects: [],
    selectedProjectId: null,
    brief: null,
    research: null,
    outline: null,
    searchPages: null,
    slidePlan: null,
    svgArtifact: null,
    selectedSlideId: null,
    isBusy: false,
    draftEditState: null,
    isSaving: false,
    regeneratingSlideId: null,
    reviewArtifact: null,
    isReviewing: false,
    error: null,
  });
  const [draggedSlideId, setDraggedSlideId] = useState<string | null>(null);
  const [composer, setComposer] = useState(DEFAULT_PROMPT);
  const [attachments, setAttachments] = useState<File[]>([]);
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const runtime = window.deckflow.getRuntimeInfo();
  const isMac = runtime.platform === "darwin";

  const selectedProject = useMemo(
    () =>
      workspace.projects.find(
        (project) => project.id === workspace.selectedProjectId
      ) ?? null,
    [workspace.projects, workspace.selectedProjectId]
  );

  const orderedSlides = useMemo(
    () =>
      workspace.outline?.slides.map((slide) => ({
        slide_id: slide.slide_id,
        order_no: slide.order_no,
        title: slide.title,
      })) ??
      workspace.searchPages?.pages.map((page) => ({
        slide_id: page.slide_id,
        order_no: page.order_no,
        title: page.title,
      })) ??
      workspace.slidePlan?.pages.map((page) => ({
        slide_id: page.slide_id,
        order_no: page.order_no,
        title: page.title,
      })) ??
      workspace.svgArtifact?.pages.map((page) => ({
        slide_id: page.slide_id,
        order_no: page.order_no,
        title: page.title,
      })) ??
      [],
    [workspace.outline, workspace.searchPages, workspace.slidePlan, workspace.svgArtifact]
  );

  const selectedSlideId = useMemo(
    () => workspace.selectedSlideId ?? orderedSlides[0]?.slide_id ?? null,
    [workspace.selectedSlideId, orderedSlides]
  );

  const selectedSearchPage = useMemo(
    () =>
      workspace.searchPages?.pages.find((page) => page.slide_id === selectedSlideId) ??
      workspace.searchPages?.pages[0] ??
      null,
    [workspace.searchPages, selectedSlideId]
  );

  const selectedPlanPage = useMemo(
    () =>
      workspace.slidePlan?.pages.find((page) => page.slide_id === selectedSlideId) ??
      workspace.slidePlan?.pages[0] ??
      null,
    [workspace.slidePlan, selectedSlideId]
  );

  const selectedSvgPage = useMemo(
    () =>
      workspace.svgArtifact?.pages.find((page) => page.slide_id === selectedSlideId) ??
      workspace.svgArtifact?.pages[0] ??
      null,
    [workspace.svgArtifact, selectedSlideId]
  );

  const visibleSlideCount =
    orderedSlides.length || selectedProject?.config.page_limit || 0;

  useEffect(() => {
    void bootstrap();
  }, []);

  async function bootstrap() {
    try {
      const [healthPayload, projects] = await Promise.all([
        api.health(),
        api.listProjects(),
      ]);

      startTransition(() => {
        setHealth({ status: "ready", payload: healthPayload });
        setWorkspace((current) => ({
          ...current,
          projects,
          selectedProjectId: projects[0]?.id ?? null,
          error: null,
        }));
      });

      if (projects[0]) {
        await loadProjectArtifacts(projects[0].id);
        setPageView("editor");
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to load workspace.";
      startTransition(() => {
        setHealth({ status: "error", message });
        setWorkspace((current) => ({ ...current, error: message }));
      });
    }
  }

  async function loadProjectArtifacts(projectId: string) {
    setWorkspace((current) => ({
      ...current,
      selectedProjectId: projectId,
      isBusy: true,
      error: null,
    }));

    try {
      const project = await api.getProject(projectId);
      const research = await api.getResearch(projectId).catch(() =>
        api.runResearch(projectId)
      );
      const brief = await api.getBrief(projectId).catch(() =>
        api.generateBrief(projectId)
      );
      const outline = await api.getOutline(projectId).catch(() =>
        api.generateOutline(projectId)
      );
      const searchPages = await api.getSearchPages(projectId).catch(() =>
        api.generateSearchPages(projectId)
      );
      const slidePlan = await api.getSlidePlan(projectId).catch(
        () => null as SlidePlanArtifact | null
      );
      const svgArtifact = await api.getSvg(projectId).catch(
        () => null as SvgSlideArtifact | null
      );

      startTransition(() => {
        setWorkspace((current) => ({
          ...current,
          projects: current.projects.map((item) =>
            item.id === project.id ? project : item
          ),
          selectedProjectId: project.id,
          brief,
          research,
          outline,
          searchPages,
          slidePlan,
          svgArtifact,
          reviewArtifact: null,
          isReviewing: false,
          selectedSlideId:
            current.selectedSlideId ??
            outline.slides[0]?.slide_id ??
            searchPages.pages[0]?.slide_id ??
            null,
          isBusy: false,
          error: null,
        }));
      });
      addChatMessage("ai", `项目"${project.title}"已加载，可在此输入修改指令。`);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to load project.";
      startTransition(() => {
        setWorkspace((current) => ({
          ...current,
          isBusy: false,
          error: message,
        }));
      });
    }
  }

  async function handleCreateProjectFromPrompt() {
    if (!composer.trim()) {
      return;
    }

    setWorkspace((current) => ({ ...current, isBusy: true, error: null }));

    try {
      const project = await api.intakeProject(composer, attachments);

      startTransition(() => {
        setWorkspace((current) => ({
          ...current,
          projects: [project, ...current.projects],
          selectedProjectId: project.id,
          brief: null,
          research: null,
          outline: null,
          searchPages: null,
          slidePlan: null,
          svgArtifact: null,
          selectedSlideId: null,
          isBusy: false,
          error: null,
        }));
        setStage("search");
        setPageView("editor");
      });

      await loadProjectArtifacts(project.id);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to create project.";
      startTransition(() => {
        setWorkspace((current) => ({
          ...current,
          isBusy: false,
          error: message,
        }));
      });
    }
  }

  async function ensureStageArtifacts(nextStage: StageView) {
    if (!workspace.selectedProjectId) {
      return;
    }

    setWorkspace((current) => ({ ...current, isBusy: true, error: null }));

    try {
      addChatMessage("ai", `正在准备${stageLabels[nextStage]}阶段...`);
      const projectId = workspace.selectedProjectId;
      const research = workspace.research ?? (await api.getResearch(projectId).catch(() =>
        api.runResearch(projectId)
      ));
      const brief = workspace.brief ?? (await api.getBrief(projectId).catch(() =>
        api.generateBrief(projectId)
      ));
      const outline = workspace.outline ?? (await api.getOutline(projectId).catch(() =>
        api.generateOutline(projectId)
      ));
      const searchPages =
        workspace.searchPages ??
        (await api.getSearchPages(projectId).catch(() =>
          api.generateSearchPages(projectId)
        ));

      let slidePlan = workspace.slidePlan;
      let svgArtifact = workspace.svgArtifact;

      if (nextStage === "draft" || nextStage === "design") {
        slidePlan =
          slidePlan ??
          (await api.getSlidePlan(projectId).catch(() =>
            api.generateSlidePlan(projectId)
          ));
      }

      if (nextStage === "design") {
        svgArtifact =
          svgArtifact ??
          (await api.getSvg(projectId).catch(() =>
            api.generateSvg(projectId)
          ));
      }

      startTransition(() => {
        setWorkspace((current) => ({
          ...current,
          brief,
          research,
          outline,
          searchPages,
          slidePlan,
          svgArtifact,
          selectedSlideId:
            current.selectedSlideId ??
            outline.slides[0]?.slide_id ??
            searchPages.pages[0]?.slide_id ??
            null,
          isBusy: false,
          error: null,
        }));
        setStage(nextStage);
      });
      addChatMessage("ai", `${stageLabels[nextStage]}阶段已就绪，共 ${orderedSlides.length} 页。`);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to prepare stage.";
      startTransition(() => {
        setWorkspace((current) => ({
          ...current,
          isBusy: false,
          error: message,
        }));
      });
      addChatMessage("ai", `生成失败：${message}`);
    }
  }

  function initDraftEdit(page: SlidePlanPage) {
    startTransition(() => {
      setWorkspace((current) => ({
        ...current,
        draftEditState: {
          title: page.title,
          core_message: page.core_message,
          visual_focus: page.visual_focus,
          blocks: page.blocks.map((b) => ({
            block_id: b.block_id,
            title: b.title,
            content: b.content,
            emphasis: b.emphasis,
          })),
        },
      }));
    });
  }

  async function handleSaveDraftPage() {
    if (!workspace.selectedProjectId || !selectedSlideId || !workspace.draftEditState) {
      return;
    }
    setWorkspace((current) => ({ ...current, isSaving: true, error: null }));
    try {
      const updatedPage = await api.updateSlidePlanPage(
        workspace.selectedProjectId,
        selectedSlideId,
        {
          title: workspace.draftEditState.title,
          core_message: workspace.draftEditState.core_message,
          visual_focus: workspace.draftEditState.visual_focus,
          blocks: workspace.draftEditState.blocks.map((b) => ({
            block_id: b.block_id,
            title: b.title,
            content: b.content,
            emphasis: b.emphasis as "high" | "medium" | "low",
          })),
        }
      );
      startTransition(() => {
        setWorkspace((current) => ({
          ...current,
          slidePlan: current.slidePlan
            ? {
                ...current.slidePlan,
                pages: current.slidePlan.pages.map((p) =>
                  p.slide_id === updatedPage.slide_id ? updatedPage : p
                ),
              }
            : null,
          draftEditState: null,
          isSaving: false,
        }));
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "保存失败";
      startTransition(() => {
        setWorkspace((current) => ({ ...current, isSaving: false, error: message }));
      });
    }
  }

  async function handleRegenerateSvgPage(slideId: string) {
    if (!workspace.selectedProjectId) return;
    setWorkspace((current) => ({ ...current, regeneratingSlideId: slideId, error: null }));
    try {
      addChatMessage("ai", `正在重新生成第 ${workspace.svgArtifact?.pages.find(p => p.slide_id === slideId)?.order_no ?? "?"} 页设计稿...`);
      const newPage = await api.regenerateSvgPage(workspace.selectedProjectId, slideId);
      startTransition(() => {
        setWorkspace((current) => ({
          ...current,
          svgArtifact: current.svgArtifact
            ? {
                ...current.svgArtifact,
                pages: current.svgArtifact.pages.map((p) =>
                  p.slide_id === newPage.slide_id ? newPage : p
                ),
              }
            : null,
          regeneratingSlideId: null,
        }));
      });
      addChatMessage("ai", "设计稿页面已更新。");
    } catch (error) {
      const message = error instanceof Error ? error.message : "重新生成失败";
      startTransition(() => {
        setWorkspace((current) => ({ ...current, regeneratingSlideId: null, error: message }));
      });
    }
  }

  async function handleRunReview() {
    if (!workspace.selectedProjectId) return;
    setWorkspace((current) => ({ ...current, isReviewing: true, error: null }));
    try {
      const review = await api.runReview(workspace.selectedProjectId);
      startTransition(() => {
        setWorkspace((current) => ({ ...current, reviewArtifact: review, isReviewing: false }));
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "检查失败";
      startTransition(() => {
        setWorkspace((current) => ({ ...current, isReviewing: false, error: message }));
      });
    }
  }

  async function handleDrop(targetSlideId: string) {
    if (!workspace.selectedProjectId || !workspace.outline || !draggedSlideId) {
      return;
    }

    const slides = reorderSlides(
      workspace.outline.slides,
      draggedSlideId,
      targetSlideId
    );

    try {
      setWorkspace((current) => ({ ...current, isBusy: true, error: null }));
      const outline = await api.reorderOutline(
        workspace.selectedProjectId,
        slides.map((slide) => slide.slide_id)
      );
      const searchPages = await api.generateSearchPages(workspace.selectedProjectId);
      startTransition(() => {
        setWorkspace((current) => ({
          ...current,
          outline,
          searchPages,
          slidePlan: null,
          svgArtifact: null,
          selectedSlideId: targetSlideId,
          isBusy: false,
          error: null,
        }));
        setStage("search");
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to reorder outline.";
      startTransition(() => {
        setWorkspace((current) => ({
          ...current,
          isBusy: false,
          error: message,
        }));
      });
    } finally {
      setDraggedSlideId(null);
    }
  }

  function handleReturnToIntake() {
    startTransition(() => {
      setPageView("intake");
      setWorkspace((current) => ({ ...current, error: null }));
    });
  }

  function addChatMessage(role: "ai" | "user", text: string) {
    const now = new Date();
    const time = `${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}`;
    setChatMessages((prev) => [
      ...prev,
      { id: `${Date.now()}-${Math.random()}`, role, text, time },
    ]);
    setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
  }

  if (pageView === "intake") {
    const greeting = (() => {
      const h = new Date().getHours();
      if (h >= 6 && h < 12) return "早上好，";
      if (h >= 12 && h < 18) return "下午好，";
      return "晚上好，";
    })();

    const chips = ["LLMOps 研究报告", "产品发布会", "季度财报分析", "企业介绍"];

    return (
      <div className="app-shell">
        <Sidebar
          projects={workspace.projects}
          selectedProjectId={workspace.selectedProjectId}
          onSelectProject={(id) => {
            void loadProjectArtifacts(id).then(() => setPageView("editor"));
          }}
          onNewProject={() => {
            setWorkspace((current) => ({
              ...current,
              selectedProjectId: null,
              brief: null,
              research: null,
              outline: null,
              searchPages: null,
              slidePlan: null,
              svgArtifact: null,
              selectedSlideId: null,
              error: null,
            }));
            setComposer("");
            setAttachments([]);
          }}
        />

        <div className="intake-main">
          <h1 className="welcome-heading">
            {greeting}
            <br />
            准备生成什么 PPT？
          </h1>
          <p className="welcome-subtitle">AI 生成定制级、可编辑的 PPT</p>

          <div className="intake-box">
            <textarea
              placeholder="例如：请基于我上传的方案文档，做一套 14 页、科技风、适合老板汇报的 PPT，重点突出开发、调试、监控和闭环优化。"
              value={composer}
              onChange={(e) => setComposer(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  void handleCreateProjectFromPrompt();
                }
              }}
            />
            <div className="intake-box-toolbar">
              <button
                className="ghost-button"
                onClick={() => fileInputRef.current?.click()}
                type="button"
              >
                📎 上传文件
              </button>
              <div className="intake-files">
                {attachments.map((file) => (
                  <span className="file-chip" key={`${file.name}-${file.size}`}>
                    {file.name}
                  </span>
                ))}
              </div>
              <button
                className="submit-button"
                disabled={workspace.isBusy || !composer.trim()}
                onClick={() => void handleCreateProjectFromPrompt()}
                type="button"
              >
                {workspace.isBusy ? "解析中..." : "开始生成 →"}
              </button>
            </div>
          </div>

          <div className="intake-chips">
            {chips.map((chip) => (
              <button
                key={chip}
                className="intake-chip"
                onClick={() => setComposer(`请生成一套关于「${chip}」的 PPT`)}
                type="button"
              >
                {chip}
              </button>
            ))}
          </div>

          {workspace.projects.length > 0 ? (
            <div className="recent-projects">
              <div className="recent-projects-label">最近项目</div>
              <div className="recent-projects-grid">
                {workspace.projects.slice(0, 3).map((p) => (
                  <button
                    key={p.id}
                    className="recent-project-card"
                    onClick={() => {
                      setWorkspace((current) => ({ ...current, selectedProjectId: p.id }));
                      void loadProjectArtifacts(p.id).then(() => setPageView("editor"));
                    }}
                    type="button"
                  >
                    <div className="recent-project-card-title">{p.title || p.topic}</div>
                    <div className="recent-project-card-meta">
                      {new Date(p.created_at).toLocaleDateString("zh-CN")}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {workspace.error ? (
            <div className="error-banner" style={{ marginTop: 16, width: "min(680px, 100%)" }}>
              {workspace.error}
            </div>
          ) : null}
          {health.status === "error" ? (
            <div className="error-banner" style={{ marginTop: 16, width: "min(680px, 100%)" }}>
              后端不可用：{health.message}
            </div>
          ) : null}
        </div>

        <input
          hidden
          multiple
          onChange={(e) => setAttachments(Array.from(e.target.files ?? []))}
          ref={fileInputRef}
          type="file"
        />
      </div>
    );
  }

  return (
    <div className={`editor-shell ${isMac ? "editor-shell-mac" : ""}`}>
      <header className="editor-topbar">
        <div className="toolbar-left">
          <button className="back-button" onClick={handleReturnToIntake} type="button">
            返回输入
          </button>
        </div>

        <div className="toolbar-center">
          <strong>{selectedProject?.title ?? DEFAULT_TITLE}</strong>
        </div>

        <div className="toolbar-right">
          <div className="export-dropdown" style={{ position: "relative" }}>
            <button
              className="export-button"
              onClick={() => setExportMenuOpen((v) => !v)}
              type="button"
            >
              导出 ▾
            </button>
            {exportMenuOpen && workspace.selectedProjectId ? (
              <div className="export-menu">
                <button
                  className="export-menu-item"
                  onClick={() => {
                    setExportMenuOpen(false);
                    void api.exportSvg(workspace.selectedProjectId!);
                  }}
                  type="button"
                >
                  导出 SVG（zip）
                </button>
                <button
                  className="export-menu-item"
                  onClick={() => {
                    setExportMenuOpen(false);
                    void api.exportPdf(workspace.selectedProjectId!);
                  }}
                  type="button"
                >
                  导出 PDF
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </header>

      <div className="editor-body">
        <aside className="slide-rail">
          <div className="rail-stage-switch">
            {(Object.keys(stageLabels) as StageView[]).map((item) => (
              <button
                className={`stage-tab ${stage === item ? "stage-tab-active" : ""}`}
                key={item}
                onClick={() => void ensureStageArtifacts(item)}
                type="button"
              >
                {stageLabels[item]}
              </button>
            ))}
          </div>

          <div className="rail-header">
            <span>幻灯片</span>
            <strong>共 {visibleSlideCount} 页</strong>
          </div>

          <div className="slide-thumbnails">
            {orderedSlides.map((slide) => (
              <button
                className={`slide-thumb ${
                  slide.slide_id === selectedSlideId ? "slide-thumb-active" : ""
                }`}
                draggable={Boolean(workspace.outline)}
                key={slide.slide_id}
                onClick={() => {
                  startTransition(() => {
                    setWorkspace((current) => ({
                      ...current,
                      selectedSlideId: slide.slide_id,
                    }));
                  });
                }}
                onDragOver={(event) => event.preventDefault()}
                onDragStart={() => setDraggedSlideId(slide.slide_id)}
                onDrop={() => void handleDrop(slide.slide_id)}
                type="button"
              >
                <span className="slide-thumb-index">{slide.order_no}</span>
                <StageThumbnail
                  draftPage={workspace.slidePlan?.pages.find(
                    (page) => page.slide_id === slide.slide_id
                  )}
                  outlineSlide={workspace.outline?.slides.find(
                    (item) => item.slide_id === slide.slide_id
                  )}
                  searchPage={workspace.searchPages?.pages.find(
                    (page) => page.slide_id === slide.slide_id
                  )}
                  stage={stage}
                  svgPage={workspace.svgArtifact?.pages.find(
                    (page) => page.slide_id === slide.slide_id
                  )}
                  title={slide.title}
                  regeneratingSlideId={workspace.regeneratingSlideId}
                  reviewPage={workspace.reviewArtifact?.pages.find(
                    (page) => page.slide_id === slide.slide_id
                  )}
                />
              </button>
            ))}
          </div>
        </aside>

        <main className="editor-main">
          {stage === "search" ? (
            <SearchWorkspace page={selectedSearchPage} />
          ) : null}
          {stage === "draft" ? (
            <DraftWorkspace
              page={selectedPlanPage}
              brief={workspace.brief}
              editState={workspace.draftEditState}
              isSaving={workspace.isSaving}
              onInitEdit={initDraftEdit}
              onEditChange={(patch) =>
                setWorkspace((current) => ({
                  ...current,
                  draftEditState: current.draftEditState
                    ? { ...current.draftEditState, ...patch }
                    : null,
                }))
              }
              onSave={() => void handleSaveDraftPage()}
            />
          ) : null}
          {stage === "design" ? (
            <DesignWorkspace
              page={selectedSvgPage}
              isRegenerating={workspace.regeneratingSlideId === selectedSlideId}
              onRegenerate={() =>
                selectedSlideId ? void handleRegenerateSvgPage(selectedSlideId) : undefined
              }
              reviewPage={
                workspace.reviewArtifact?.pages.find(
                  (p) => p.slide_id === selectedSlideId
                ) ?? null
              }
              isReviewing={workspace.isReviewing}
              onRunReview={() => void handleRunReview()}
            />
          ) : null}

          {workspace.error ? <div className="error-banner">{workspace.error}</div> : null}
        </main>
      </div>
    </div>
  );
}

function SearchWorkspace({
  page,
}: {
  page: SearchPage | null;
}) {
  const [selectedIdx, setSelectedIdx] = useState(0);

  useEffect(() => {
    setSelectedIdx(0);
  }, [page?.slide_id]);

  if (!page) {
    return (
      <div className="search-layout">
        <div className="citation-empty">等待后端生成搜索内容...</div>
      </div>
    );
  }

  const citations = page.citations;
  const selected = citations[selectedIdx] ?? null;

  if (citations.length === 0) {
    return (
      <div className="search-layout">
        <div className="citation-empty">当前页暂无引用来源</div>
      </div>
    );
  }

  return (
    <div className="search-layout">
      <div className="citation-list">
        {citations.map((citation, idx) => (
          <button
            key={citation.url}
            className={`citation-list-item ${idx === selectedIdx ? "citation-list-item-active" : ""}`}
            onClick={() => setSelectedIdx(idx)}
            type="button"
          >
            <strong>{citation.title || citation.url}</strong>
            <span>{citation.url}</span>
          </button>
        ))}
      </div>

      <div className="citation-detail">
        {selected ? (
          <>
            <h3 className="citation-detail-title">{selected.title || "（无标题）"}</h3>
            <a
              className="citation-detail-url"
              href={selected.url}
              rel="noreferrer"
              target="_blank"
            >
              {selected.url}
            </a>
            <p className="citation-detail-snippet">{selected.snippet}</p>
          </>
        ) : null}
      </div>
    </div>
  );
}

function DraftWorkspace({
  page,
  brief,
  editState,
  isSaving,
  onInitEdit,
  onEditChange,
  onSave,
}: {
  page: SlidePlanPage | null;
  brief: RequirementBrief | null;
  editState: {
    title: string;
    core_message: string;
    visual_focus: string;
    blocks: Array<{ block_id: string; title: string; content: string; emphasis: string }>;
  } | null;
  isSaving: boolean;
  onInitEdit: (page: SlidePlanPage) => void;
  onEditChange: (patch: {
    title?: string;
    core_message?: string;
    visual_focus?: string;
    blocks?: Array<{ block_id: string; title: string; content: string; emphasis: string }>;
  }) => void;
  onSave: () => void;
}) {
  if (!page) {
    return (
      <div className="stage-preview-shell">
        <div className="stage-preview-frame">
          <EmptyPreview description="等待后端生成 slide_plan。" />
        </div>
      </div>
    );
  }

  const isEditing = editState !== null;
  const display = editState ?? {
    title: page.title,
    core_message: page.core_message,
    visual_focus: page.visual_focus,
    blocks: page.blocks,
  };

  return (
    <div className="stage-preview-shell">
      <div className="stage-preview-header">
        <span className="eyebrow">初稿</span>
        <strong style={{ fontSize: 15, marginRight: "auto" }}>{page.title}</strong>
        {!isEditing ? (
          <button className="ghost-button" onClick={() => onInitEdit(page)} type="button">
            编辑
          </button>
        ) : (
          <button
            className="submit-button"
            disabled={isSaving}
            onClick={onSave}
            type="button"
          >
            {isSaving ? "保存中..." : "保存"}
          </button>
        )}
      </div>

      <div className="stage-preview-frame">
        <div className="artboard-wrapper">
          <div className="artboard">
            <div className="artboard-title">
              <span className="title-marker" />
              <div className="title-copy">
                {isEditing ? (
                  <textarea
                    className="title-input"
                    value={display.title}
                    rows={2}
                    onChange={(e) => onEditChange({ title: e.target.value })}
                  />
                ) : (
                  <h2>{display.title}</h2>
                )}
              </div>
              <div className="title-meta">{`第 ${page.order_no.toString().padStart(2, "0")} 页`}</div>
            </div>

            <div className="artboard-grid">
              {display.blocks.slice(0, 4).map((block, index) => (
                <section className="art-card" key={block.block_id}>
                  <div className="art-card-head">
                    {isEditing ? (
                      <input
                        className="draft-edit-input"
                        value={block.title}
                        onChange={(e) => {
                          const next = display.blocks.map((b, i) =>
                            i === index ? { ...b, title: e.target.value } : b
                          );
                          onEditChange({ blocks: next });
                        }}
                      />
                    ) : (
                      <h3>{block.title}</h3>
                    )}
                    <span className="blue-tag">
                      {(page.blocks[index] as { kind?: string })?.kind ?? ""}
                    </span>
                  </div>
                  {isEditing ? (
                    <textarea
                      className="card-textarea"
                      value={block.content}
                      rows={4}
                      onChange={(e) => {
                        const next = display.blocks.map((b, i) =>
                          i === index ? { ...b, content: e.target.value } : b
                        );
                        onEditChange({ blocks: next });
                      }}
                    />
                  ) : (
                    <p className="canvas-copy">{block.content}</p>
                  )}
                  {isEditing && (
                    <div className="draft-block-reorder">
                      <button
                        className="ghost-button"
                        disabled={index === 0}
                        onClick={() => {
                          const next = [...display.blocks];
                          [next[index - 1], next[index]] = [next[index], next[index - 1]];
                          onEditChange({ blocks: next });
                        }}
                        type="button"
                      >
                        ↑
                      </button>
                      <button
                        className="ghost-button"
                        disabled={index === display.blocks.length - 1}
                        onClick={() => {
                          const next = [...display.blocks];
                          [next[index], next[index + 1]] = [next[index + 1], next[index]];
                          onEditChange({ blocks: next });
                        }}
                        type="button"
                      >
                        ↓
                      </button>
                    </div>
                  )}
                </section>
              ))}
            </div>

            {brief && !isEditing ? (
              <div className="status-strip status-strip-soft" style={{ marginTop: 18 }}>
                {`版式：${page.suggested_layout} · 视觉重心：${page.visual_focus} · 语气：${brief.tone}`}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

function DesignWorkspace({
  page,
  isRegenerating,
  onRegenerate,
  reviewPage,
  isReviewing,
  onRunReview,
}: {
  page: SvgSlidePage | null;
  isRegenerating: boolean;
  onRegenerate: () => void;
  reviewPage: ReviewPage | null;
  isReviewing: boolean;
  onRunReview: () => void;
}) {
  if (!page) {
    return (
      <div className="stage-preview-shell">
        <div className="stage-preview-frame">
          <EmptyPreview description="等待后端生成 SVG 设计稿。" />
        </div>
      </div>
    );
  }

  return (
    <div className="stage-preview-shell">
      <div className="stage-preview-header">
        <span className="eyebrow">设计稿</span>
        <strong style={{ fontSize: 15, marginRight: "auto" }}>{page.title}</strong>
        <div className="design-action-bar">
          <button
            className="ghost-button"
            disabled={isRegenerating}
            onClick={onRegenerate}
            type="button"
          >
            {isRegenerating ? "生成中..." : "重新生成"}
          </button>
          <button
            className="ghost-button"
            disabled={isReviewing}
            onClick={onRunReview}
            type="button"
          >
            {isReviewing ? "检查中..." : "检查"}
          </button>
        </div>
      </div>

      <div className="stage-preview-frame">
        <div className="svg-preview-stage">
          <div
            className="svg-preview-surface"
            dangerouslySetInnerHTML={{ __html: page.svg }}
          />
        </div>
      </div>

      {reviewPage ? (
        <div className={`review-panel ${reviewPage.passed ? "" : "review-panel-warning"}`}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              marginBottom: reviewPage.issues.length ? 10 : 0,
            }}
          >
            <strong>{reviewPage.passed ? "✓ 检查通过" : "⚠ 检查发现问题"}</strong>
            <span className="topic-pill">{`${reviewPage.issues.length} 条`}</span>
          </div>
          {reviewPage.issues.length > 0 ? (
            <ul className="fact-list">
              {reviewPage.issues.map((issue) => (
                <li key={issue.code}>
                  <strong>[{issue.severity}]</strong> {issue.detail}
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ margin: 0, color: "var(--muted)" }}>所有检查项均通过。</p>
          )}
        </div>
      ) : null}
    </div>
  );
}

function StageThumbnail({
  stage,
  title,
  outlineSlide,
  searchPage,
  draftPage,
  svgPage,
  regeneratingSlideId,
  reviewPage,
}: {
  stage: StageView;
  title: string;
  outlineSlide: OutlineSlide | undefined;
  searchPage: SearchPage | undefined;
  draftPage: SlidePlanPage | undefined;
  svgPage: SvgSlidePage | undefined;
  regeneratingSlideId: string | null;
  reviewPage?: ReviewPage;
}) {
  return (
    <div className="slide-thumb-canvas">
      <div className="slide-thumb-title">{title}</div>

      {stage === "search" ? (
        searchPage ? (
          <div className="slide-thumb-search">
            <div className="slide-thumb-line" />
            <div className="slide-thumb-line short" />
            <div className="slide-thumb-grid">
              <span>{`${searchPage.facts.length} 条事实`}</span>
              <span>{`${searchPage.citations.length} 个来源`}</span>
            </div>
          </div>
        ) : (
          <ThumbnailLoading />
        )
      ) : null}

      {stage === "draft" ? (
        draftPage ? (
          <div className="slide-thumb-draft">
            <div className="slide-thumb-line" />
            <div className="slide-thumb-line short" />
            <div className="slide-thumb-copy">{draftPage.blocks[0]?.content ?? draftPage.core_message}</div>
          </div>
        ) : (
          <ThumbnailLoading />
        )
      ) : null}

      {stage === "design" && svgPage ? (
        <div className="slide-thumb-design-wrapper">
          {regeneratingSlideId === svgPage.slide_id ? (
            <ThumbnailLoading />
          ) : (
            <div
              className="slide-thumb-design-live"
              dangerouslySetInnerHTML={{ __html: svgPage.svg }}
            />
          )}
          {reviewPage && !reviewPage.passed ? (
            <span className="slide-thumb-issue-dot" title="检查发现问题" />
          ) : null}
        </div>
      ) : stage === "design" ? (
        <ThumbnailLoading />
      ) : null}

      {!searchPage && !draftPage && !svgPage && outlineSlide ? (
        <div className="slide-thumb-copy">{outlineSlide.key_message}</div>
      ) : null}
    </div>
  );
}

function ThumbnailLoading() {
  return (
    <div className="slide-thumb-loading">
      <div className="slide-thumb-line" />
      <div className="slide-thumb-line short" />
    </div>
  );
}

function EmptyPreview({ description }: { description: string }) {
  return (
    <div className="empty-preview">
      <strong>等待生成</strong>
      <p>{description}</p>
    </div>
  );
}

function reorderSlides(
  slides: OutlineSlide[],
  sourceId: string,
  targetId: string
): OutlineSlide[] {
  const next = [...slides];
  const sourceIndex = next.findIndex((slide) => slide.slide_id === sourceId);
  const targetIndex = next.findIndex((slide) => slide.slide_id === targetId);

  if (sourceIndex === -1 || targetIndex === -1 || sourceIndex === targetIndex) {
    return next;
  }

  const [moved] = next.splice(sourceIndex, 1);
  next.splice(targetIndex, 0, moved);

  return next.map((slide, index) => ({ ...slide, order_no: index + 1 }));
}

function Sidebar({
  projects,
  selectedProjectId,
  onSelectProject,
  onNewProject,
}: {
  projects: Project[];
  selectedProjectId: string | null;
  onSelectProject: (id: string) => void;
  onNewProject: () => void;
}) {
  const stageBadge = (p: Project) => {
    if (p.status === "draft") return null;
    return <span className="project-item-badge project-item-badge-blue">进行中</span>;
  };

  return (
    <aside className="app-sidebar">
      <div className="sidebar-brand">ppt-agent</div>

      <button className="sidebar-new-btn" onClick={onNewProject} type="button">
        ＋ 新建项目
      </button>

      {projects.length > 0 ? (
        <>
          <div className="sidebar-section-label">最近</div>
          {projects.map((p) => (
            <button
              key={p.id}
              className={`project-item ${p.id === selectedProjectId ? "project-item-active" : ""}`}
              onClick={() => onSelectProject(p.id)}
              type="button"
            >
              <span className="project-item-title">{p.title || p.topic}</span>
              {stageBadge(p)}
            </button>
          ))}
        </>
      ) : (
        <div className="sidebar-empty">暂无记录</div>
      )}

      <div className="sidebar-spacer" />
    </aside>
  );
}
