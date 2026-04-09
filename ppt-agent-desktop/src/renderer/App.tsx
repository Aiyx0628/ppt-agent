import { startTransition, useEffect, useMemo, useRef, useState } from "react";

import { api } from "./services/api";
import type {
  HealthResponse,
  OutlineArtifact,
  OutlineSlide,
  Project,
  RequirementBrief,
  ResearchPack,
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
  selectedSlideId: string | null;
  isBusy: boolean;
  error: string | null;
};

type DraftModel = {
  title: string;
  efficiencyLabel: string;
  bulletText: string;
  footer: string;
  chartSubtitle: string;
  loopTitle: string;
  loopSteps: string;
  loopSummary: string;
  integrationTitle: string;
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
    selectedSlideId: null,
    isBusy: false,
    error: null,
  });
  const [draggedSlideId, setDraggedSlideId] = useState<string | null>(null);
  const [composer, setComposer] = useState(DEFAULT_PROMPT);
  const [attachments, setAttachments] = useState<File[]>([]);
  const [draftModels, setDraftModels] = useState<Record<string, DraftModel>>({});
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

  const selectedSlide = useMemo(() => {
    const slides = workspace.outline?.slides ?? [];
    return (
      slides.find((slide) => slide.slide_id === workspace.selectedSlideId) ??
      slides[0] ??
      null
    );
  }, [workspace.outline, workspace.selectedSlideId]);

  const visibleSlideCount =
    workspace.outline?.slides.length ?? selectedProject?.config.page_limit ?? 14;

  const toolbarTitle = selectedProject?.title || DEFAULT_TITLE;

  const activeDraft = useMemo(() => {
    if (!selectedSlide) {
      return null;
    }
    return draftModels[selectedSlide.slide_id] ?? makeDraftModel(selectedSlide);
  }, [draftModels, selectedSlide]);

  useEffect(() => {
    void bootstrap();
  }, []);

  useEffect(() => {
    if (!selectedSlide) {
      return;
    }

    setDraftModels((current) => {
      if (current[selectedSlide.slide_id]) {
        return current;
      }
      return {
        ...current,
        [selectedSlide.slide_id]: makeDraftModel(selectedSlide),
      };
    });
  }, [selectedSlide]);

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
        }));
      });

      if (projects[0]) {
        setPageView("editor");
        await loadProjectArtifacts(projects[0].id);
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
      const brief = await api
        .getBrief(projectId)
        .catch(() => api.generateBrief(projectId));
      const research = await api
        .getResearch(projectId)
        .catch(() => null as ResearchPack | null);
      const outline = await api
        .getOutline(projectId)
        .catch(() => null as OutlineArtifact | null);

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
          selectedSlideId: outline?.slides[0]?.slide_id ?? null,
          isBusy: false,
        }));
        setPageView("editor");
      });
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
      const parsed = parsePrompt(composer, attachments);
      const project = await api.createProject(parsed);

      startTransition(() => {
        setWorkspace((current) => ({
          ...current,
          projects: [project, ...current.projects],
          selectedProjectId: project.id,
          brief: null,
          research: null,
          outline: null,
          selectedSlideId: null,
          isBusy: false,
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

  async function handleGenerateOutline() {
    if (!workspace.selectedProjectId) return;

    setWorkspace((current) => ({ ...current, isBusy: true, error: null }));
    try {
      const outline = await api.generateOutline(workspace.selectedProjectId);
      startTransition(() => {
        setWorkspace((current) => ({
          ...current,
          outline,
          selectedSlideId: outline.slides[0]?.slide_id ?? null,
          isBusy: false,
        }));
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to generate outline.";
      startTransition(() => {
        setWorkspace((current) => ({
          ...current,
          isBusy: false,
          error: message,
        }));
      });
    }
  }

  async function handleEnsureStage(nextStage: StageView) {
    if (nextStage !== "search" && !workspace.outline && workspace.selectedProjectId) {
      await handleGenerateOutline();
    }

    startTransition(() => {
      setStage(nextStage);
    });
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

    startTransition(() => {
      setWorkspace((current) => ({
        ...current,
        outline: current.outline ? { ...current.outline, slides } : current.outline,
      }));
    });

    try {
      const outline = await api.reorderOutline(
        workspace.selectedProjectId,
        slides.map((slide) => slide.slide_id)
      );
      startTransition(() => {
        setWorkspace((current) => ({ ...current, outline }));
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to reorder outline.";
      startTransition(() => {
        setWorkspace((current) => ({ ...current, error: message }));
      });
    } finally {
      setDraggedSlideId(null);
    }
  }

  function updateDraft(
    key: keyof DraftModel,
    value: string,
    slideId: string | undefined
  ) {
    if (!slideId) return;
    setDraftModels((current) => ({
      ...current,
      [slideId]: {
        ...(current[slideId] ?? makeDraftModel(selectedSlide ?? null)),
        [key]: value,
      },
    }));
  }

  if (pageView === "intake") {
    return (
      <div className="intake-shell">
        <section className="intake-panel">
          <div className="intake-brand">DeckFlow</div>

          <div className="intake-composer">
            <textarea
              className="intake-textarea"
              placeholder="例如：请基于我上传的方案文档，做一套 14 页、科技风、适合老板汇报的 PPT，重点突出开发、调试、监控和闭环优化。"
              rows={7}
              value={composer}
              onChange={(event) => setComposer(event.target.value)}
            />

            <div className="intake-toolbar">
              <button
                className="ghost-button"
                onClick={() => fileInputRef.current?.click()}
                type="button"
              >
                上传文件
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
                {workspace.isBusy ? "解析中..." : "开始生成"}
              </button>
            </div>
          </div>

          {workspace.error ? <div className="error-banner">{workspace.error}</div> : null}
        </section>

        <input
          hidden
          multiple
          onChange={(event) =>
            setAttachments(Array.from(event.target.files ?? []))
          }
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
          <button className="search-entry" type="button">
            搜索入口
          </button>
          <nav className="stage-tabs" aria-label="Workflow stages">
            {(Object.keys(stageLabels) as StageView[]).map((item) => (
              <button
                className={`stage-tab ${stage === item ? "stage-tab-active" : ""}`}
                key={item}
                onClick={() => void handleEnsureStage(item)}
                type="button"
              >
                {stageLabels[item]}
              </button>
            ))}
          </nav>
        </div>

        <div className="toolbar-center">
          <strong>{toolbarTitle}</strong>
          <span className="preview-pill">预览</span>
        </div>

        <div className="toolbar-right">
          <button className="ghost-button" type="button">
            放映
          </button>
          <button className="export-button" type="button">
            导出
          </button>
        </div>
      </header>

      <div className="editor-body">
        <aside className="slide-rail">
          <div className="rail-header">
            <span>幻灯片</span>
            <strong>共 {visibleSlideCount} 页</strong>
          </div>

          <div className="slide-thumbnails">
            {workspace.outline
              ? workspace.outline.slides.map((slide) => (
                  <button
                    className={`slide-thumb ${
                      slide.slide_id === selectedSlide?.slide_id
                        ? "slide-thumb-active"
                        : ""
                    }`}
                    draggable
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
                    <div className="slide-thumb-canvas">
                      <div className="slide-thumb-title">{slide.title}</div>
                      <div className="slide-thumb-line" />
                      <div className="slide-thumb-grid">
                        <span />
                        <span />
                        <span />
                      </div>
                    </div>
                  </button>
                ))
              : Array.from({ length: visibleSlideCount }).map((_, index) => (
                  <div className="slide-thumb slide-thumb-loading" key={index}>
                    <span className="slide-thumb-index">{index + 1}</span>
                    <div className="slide-thumb-canvas">
                      <div className="slide-thumb-line loading-block" />
                      <div className="slide-thumb-grid">
                        <span className="loading-block" />
                        <span className="loading-block" />
                        <span className="loading-block" />
                      </div>
                    </div>
                  </div>
                ))}
          </div>
        </aside>

        <main className="editor-main">
          {stage === "search" ? (
            <SearchPanel research={workspace.research} brief={workspace.brief} />
          ) : null}

          {stage === "draft" ? (
            <DraftPanel
              draft={activeDraft}
              selectedSlide={selectedSlide}
              onUpdate={(key, value) =>
                updateDraft(key, value, selectedSlide?.slide_id)
              }
            />
          ) : null}

          {stage === "design" ? (
            <DesignPanel draft={activeDraft} selectedSlide={selectedSlide} />
          ) : null}

          {workspace.error ? <div className="error-banner">{workspace.error}</div> : null}
        </main>
      </div>
    </div>
  );
}

function SearchPanel({
  research,
  brief,
}: {
  research: ResearchPack | null;
  brief: RequirementBrief | null;
}) {
  const citations = (research?.topics ?? []).flatMap((topic) =>
    topic.citations.map((citation) => ({ ...citation, topic: topic.name }))
  );

  return (
    <section className="workspace-stage">
      <div className="canvas-shell">
        <div className="canvas-shell-inner search-results">
          <div className="search-column">
            <div className="panel-heading">
              <span>研究摘要</span>
              <strong>{research ? `Research v${research.version}` : "等待 research"}</strong>
            </div>
            <div className="search-summary">
              <strong>{brief?.goal ?? "正在准备页级搜索内容"}</strong>
              <p>{research?.summary ?? "系统会根据资料、需求和外部来源生成 research_pack。"}</p>
            </div>
            <div className="cluster-list">
              {(research?.topics ?? []).map((topic, index) => (
                <article className="cluster-card" key={topic.name}>
                  <div className="cluster-top">
                    <strong>{`${index + 1}. ${topic.name}`}</strong>
                    <span>{topic.cluster}</span>
                  </div>
                  <p>{topic.summary}</p>
                  <ul>
                    {topic.facts.map((fact) => (
                      <li key={fact}>{fact}</li>
                    ))}
                  </ul>
                </article>
              ))}
            </div>
          </div>

          <div className="search-column">
            <div className="panel-heading">
              <span>来源引用</span>
              <strong>可点击网页地址</strong>
            </div>
            <div className="citation-list">
              {citations.length ? (
                citations.map((citation) => (
                  <a
                    className="citation-card"
                    href={citation.url}
                    key={`${citation.topic}-${citation.url}`}
                    rel="noreferrer"
                    target="_blank"
                  >
                    <div className="citation-tag">{citation.topic}</div>
                    <strong>{citation.title}</strong>
                    <span>{citation.url}</span>
                    <p>{citation.snippet}</p>
                  </a>
                ))
              ) : (
                <div className="search-summary">
                  <strong>等待 research_pack</strong>
                  <p>这里会展示检索到的网页、摘要结论和可点击引用地址。</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function DraftPanel({
  selectedSlide,
  draft,
  onUpdate,
}: {
  selectedSlide: OutlineSlide | null;
  draft: DraftModel | null;
  onUpdate: (key: keyof DraftModel, value: string) => void;
}) {
  return (
    <section className="workspace-stage">
      <div className="canvas-shell">
        <SlideCanvas
          draft={draft}
          editable
          pageNo={selectedSlide?.order_no ?? 10}
          title={selectedSlide?.title ?? DEFAULT_TITLE}
          onUpdate={onUpdate}
        />
      </div>
    </section>
  );
}

function DesignPanel({
  selectedSlide,
  draft,
}: {
  selectedSlide: OutlineSlide | null;
  draft: DraftModel | null;
}) {
  return (
    <section className="workspace-stage">
      <div className="canvas-shell">
        <SlideCanvas
          draft={draft}
          editable={false}
          pageNo={selectedSlide?.order_no ?? 10}
          title={selectedSlide?.title ?? DEFAULT_TITLE}
        />
      </div>
    </section>
  );
}

function SlideCanvas({
  title,
  pageNo,
  draft,
  editable,
  onUpdate,
}: {
  title: string;
  pageNo: number;
  draft: DraftModel | null;
  editable: boolean;
  onUpdate?: (key: keyof DraftModel, value: string) => void;
}) {
  const model = draft ?? makeDraftModel(null);
  const displayTitle = model.title || title;

  return (
    <div className="artboard-wrapper">
      <div className="artboard">
        <div className="artboard-title">
          <span className="title-marker" />
          <div className="title-copy">
            {editable ? (
              <textarea
                className="title-input"
                rows={2}
                value={displayTitle}
                onChange={(event) => onUpdate?.("title", event.target.value)}
              />
            ) : (
              <h2>{displayTitle}</h2>
            )}
          </div>
          <div className="title-meta">Neural Blueprint Style | Page {pageNo.toString().padStart(2, "0")}</div>
        </div>

        <div className="artboard-grid">
          <section className="art-card">
            <div className="art-card-head">
              <h3>敏捷开发与深度调试</h3>
              <span className="blue-tag">{model.efficiencyLabel}</span>
            </div>
            {editable ? (
              <textarea
                className="card-textarea"
                rows={7}
                value={model.bulletText}
                onChange={(event) => onUpdate?.("bulletText", event.target.value)}
              />
            ) : (
              <ul className="bullet-list">
                {model.bulletText.split("\n").map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
            <div className="status-strip">{model.footer}</div>
          </section>

          <section className="art-card">
            <div className="art-card-head">
              <h3>全栈可观测性监控</h3>
              <span className="card-subtitle">{model.chartSubtitle}</span>
            </div>
            <div className="chart-placeholder">
              <div className="chart-grid" />
              <div className="chart-line chart-line-a" />
              <div className="chart-line chart-line-b" />
            </div>
          </section>

          <section className="art-card">
            <div className="art-card-head">
              <h3>数据驱动的闭环优化</h3>
            </div>
            <div className="loop-layout">
              <div className="loop-circle">LOOP</div>
              {editable ? (
                <textarea
                  className="card-textarea"
                  rows={7}
                  value={model.loopSteps}
                  onChange={(event) => onUpdate?.("loopSteps", event.target.value)}
                />
              ) : (
                <ol className="number-list">
                  {model.loopSteps.split("\n").map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ol>
              )}
            </div>
            <div className="status-strip status-strip-soft">{model.loopSummary}</div>
          </section>

          <section className="art-card">
            <div className="art-card-head">
              <h3>开放的 Ops 生态集成</h3>
              <span className="card-subtitle">Tools & Integrations</span>
            </div>
            <div className="integrations-box">
              <span>LangSmith</span>
              <span>Langfuse</span>
              <span>Opik</span>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function parsePrompt(prompt: string, files: File[]) {
  const pageMatch = prompt.match(/(\d{1,2})\s*页/);
  const pageLimit = pageMatch ? Number(pageMatch[1]) : 14;
  const style_pref = prompt.includes("商务")
    ? "商务"
    : prompt.includes("简洁")
      ? "简洁"
      : "科技";
  const scenario = prompt.includes("培训")
    ? "培训"
    : prompt.includes("路演")
      ? "路演"
      : prompt.includes("总结")
        ? "总结"
        : "汇报";

  const titleSeed =
    files[0]?.name.replace(/\.[^.]+$/, "") ||
    prompt.split(/[。\n]/)[0].trim() ||
    DEFAULT_TITLE;

  return {
    title: titleSeed.slice(0, 48),
    topic: `${prompt}${files.length ? `\n\n附件：${files.map((file) => file.name).join("、")}` : ""}`,
    config: {
      scenario,
      audience: "产品负责人 / 决策层",
      style_pref,
      page_limit: Math.min(Math.max(pageLimit, 4), 20),
      research_enabled: true,
      narration_enabled: false,
    },
  };
}

function makeDraftModel(slide: OutlineSlide | null): DraftModel {
  return {
    title: slide?.title ?? DEFAULT_TITLE,
    efficiencyLabel: "效率提升 10 倍",
    bulletText: [
      "多 Agent 协同开发与调试",
      "统一的 Prompt / Tool / Workflow 管理",
      "一套流程覆盖开发、测试和上线观测",
    ].join("\n"),
    footer: "状态：Draft Ready",
    chartSubtitle: "覆盖开发、调试、监控与评估",
    loopTitle: "Human-in-the-loop",
    loopSteps: ["采集反馈", "分析问题", "更新策略"].join("\n"),
    loopSummary: "Human-in-the-loop：让生成、评估与人工判断形成闭环。",
    integrationTitle: "开放生态",
  };
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
