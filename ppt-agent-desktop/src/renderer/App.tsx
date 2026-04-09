import { startTransition, useEffect, useMemo, useRef, useState } from "react";

import { api } from "./services/api";
import type {
  HealthResponse,
  OutlineArtifact,
  OutlineSlide,
  Project,
  RequirementBrief,
  ResearchPack,
  ResearchTopic,
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

type SlideContext = {
  title: string;
  pageNo: number;
  section: string;
  type: string;
  keyMessage: string;
  audience: string;
  scenario: string;
  style: string;
  facts: string[];
  citations: Array<{ title: string; url: string; snippet: string }>;
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

  const slideContext = useMemo(
    () => buildSlideContext(selectedProject, selectedSlide, workspace.brief, workspace.research),
    [selectedProject, selectedSlide, workspace.brief, workspace.research]
  );

  const visibleSlideCount =
    workspace.outline?.slides.length ?? selectedProject?.config.page_limit ?? 0;

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
      const brief = await api.getBrief(projectId).catch(() => api.generateBrief(projectId));
      const research = await api.getResearch(projectId).catch(() => null as ResearchPack | null);
      const outline = await api.getOutline(projectId).catch(() => null as OutlineArtifact | null);

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
          error: null,
        }));
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
      const project = await api.createProject(parsePrompt(composer, attachments));

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

  async function handleEnsureStage(nextStage: StageView) {
    if (nextStage !== "search" && !workspace.outline && workspace.selectedProjectId) {
      await handleGenerateOutline();
    }

    startTransition(() => {
      setStage(nextStage);
    });
  }

  async function handleGenerateOutline() {
    if (!workspace.selectedProjectId) {
      return;
    }

    setWorkspace((current) => ({ ...current, isBusy: true, error: null }));

    try {
      const outline = await api.generateOutline(workspace.selectedProjectId);
      startTransition(() => {
        setWorkspace((current) => ({
          ...current,
          outline,
          selectedSlideId: outline.slides[0]?.slide_id ?? null,
          isBusy: false,
          error: null,
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

  function handleReturnToIntake() {
    startTransition(() => {
      setPageView("intake");
      setWorkspace((current) => ({ ...current, error: null }));
    });
  }

  if (pageView === "intake") {
    return (
      <div className="intake-shell">
        <section className="intake-panel">
          <div className="intake-brand">DeckFlow</div>
          <div className="intake-caption">上传文本资料，然后用一句话输入你的所有要求。</div>

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
          {health.status === "error" ? (
            <div className="error-banner">后端不可用：{health.message}</div>
          ) : null}
        </section>

        <input
          hidden
          multiple
          onChange={(event) => setAttachments(Array.from(event.target.files ?? []))}
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
          <div className="rail-stage-switch">
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
          </div>

          <div className="rail-header">
            <span>幻灯片</span>
            <strong>共 {visibleSlideCount} 页</strong>
          </div>

          <div className="slide-thumbnails">
            {(workspace.outline?.slides ?? []).map((slide) => {
              const context = buildSlideContext(
                selectedProject,
                slide,
                workspace.brief,
                workspace.research
              );

              return (
                <button
                  className={`slide-thumb ${
                    slide.slide_id === selectedSlide?.slide_id ? "slide-thumb-active" : ""
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
                  <StageThumbnail stage={stage} context={context} />
                </button>
              );
            })}
          </div>
        </aside>

        <main className="editor-main">
          <section className="workspace-layout">
            <div className="workspace-panel workspace-panel-content">
              {stage === "search" ? <SearchWorkspace context={slideContext} /> : null}
              {stage === "draft" ? <DraftWorkspace context={slideContext} /> : null}
              {stage === "design" ? <DesignWorkspace context={slideContext} /> : null}
            </div>

            <div className="workspace-panel workspace-panel-preview">
              <div className="preview-header">
                <div>
                  <span>当前页面</span>
                  <strong>{slideContext.title}</strong>
                </div>
                <div className="status-chip">{stageLabels[stage]}</div>
              </div>

              {stage === "search" ? <SearchPreview context={slideContext} /> : null}
              {stage === "draft" ? <SlideCanvas context={slideContext} polished={false} /> : null}
              {stage === "design" ? <SlideCanvas context={slideContext} polished /> : null}
            </div>
          </section>

          {workspace.error ? <div className="error-banner">{workspace.error}</div> : null}
        </main>
      </div>
    </div>
  );
}

function SearchWorkspace({ context }: { context: SlideContext }) {
  return (
    <>
      <div className="workspace-section-heading">
        <span>搜索结果</span>
        <strong>{`第 ${context.pageNo} 页研究内容`}</strong>
      </div>

      <div className="workspace-card workspace-card-primary">
        <div className="workspace-meta-row">
          <span className="eyebrow">页面主题</span>
          <span className="status-chip status-chip-muted">{context.section}</span>
        </div>
        <h3>{context.title}</h3>
        <p>{context.keyMessage}</p>
      </div>

      <div className="workspace-card-list">
        <article className="workspace-card">
          <div className="workspace-meta-row">
            <strong>已解析事实</strong>
            <span className="topic-pill">{context.facts.length} 条</span>
          </div>
          <ul className="fact-list">
            {context.facts.map((fact) => (
              <li key={fact}>{fact}</li>
            ))}
          </ul>
        </article>
      </div>

      <div className="workspace-card-list citations-grid">
        {context.citations.length ? (
          context.citations.map((citation) => (
            <a
              className="workspace-card citation-card"
              href={citation.url}
              key={citation.url}
              rel="noreferrer"
              target="_blank"
            >
              <div className="citation-tag">引用</div>
              <strong>{citation.title}</strong>
              <span>{citation.url}</span>
              <p>{citation.snippet}</p>
            </a>
          ))
        ) : (
          <article className="workspace-card">
            <strong>暂无外部引用</strong>
            <p>当前页面只展示来自后端真实 research 数据。外部联网检索尚未接入时，这里不会伪造来源。</p>
          </article>
        )}
      </div>
    </>
  );
}

function DraftWorkspace({ context }: { context: SlideContext }) {
  return (
    <>
      <div className="workspace-section-heading">
        <span>初稿内容</span>
        <strong>{context.title}</strong>
      </div>

      <div className="workspace-card workspace-card-primary">
        <div className="workspace-meta-row">
          <strong>核心表达</strong>
          <span className="topic-pill">{context.type}</span>
        </div>
        <p>{context.keyMessage}</p>
      </div>

      <div className="workspace-card-list">
        <article className="workspace-card">
          <div className="workspace-meta-row">
            <strong>页面结构</strong>
            <span className="topic-pill">{context.section}</span>
          </div>
          <ul className="fact-list">
            <li>{`受众：${context.audience}`}</li>
            <li>{`场景：${context.scenario}`}</li>
            <li>{`风格：${context.style}`}</li>
          </ul>
        </article>

        <article className="workspace-card">
          <div className="workspace-meta-row">
            <strong>支撑信息</strong>
            <span className="topic-pill">{context.facts.length} 条</span>
          </div>
          <ul className="fact-list">
            {context.facts.slice(0, 4).map((fact) => (
              <li key={fact}>{fact}</li>
            ))}
          </ul>
        </article>
      </div>
    </>
  );
}

function DesignWorkspace({ context }: { context: SlideContext }) {
  return (
    <>
      <div className="workspace-section-heading">
        <span>设计稿</span>
        <strong>{context.title}</strong>
      </div>

      <div className="workspace-card workspace-card-primary">
        <div className="workspace-meta-row">
          <strong>版式指令</strong>
          <span className="topic-pill">2 × 2 Grid</span>
        </div>
        <p>{`当前设计稿继续使用第 ${context.pageNo} 页的真实标题、关键信息和 research 事实，不再注入固定示例文案。`}</p>
      </div>

      <div className="workspace-card-list">
        <article className="workspace-card">
          <strong>设计约束</strong>
          <ul className="fact-list">
            <li>{`页面类型：${context.type}`}</li>
            <li>{`视觉风格：${context.style}`}</li>
            <li>{`引用数量：${context.citations.length}`}</li>
          </ul>
        </article>
      </div>
    </>
  );
}

function SearchPreview({ context }: { context: SlideContext }) {
  return (
    <div className="research-preview-card">
      <div className="research-preview-frame">
        <div className="research-preview-page-no">{context.pageNo}</div>
        <div className="research-preview-title">{context.title}</div>
        <p className="research-preview-copy">{context.keyMessage}</p>
        <div className="research-preview-list">
          {context.facts.slice(0, 4).map((fact) => (
            <div className="research-preview-fact" key={fact}>
              {fact}
            </div>
          ))}
        </div>
      </div>

      <div className="research-preview-footer">
        <strong>{context.citations.length ? "已找到相关来源" : "暂无外部来源"}</strong>
        <p>搜索阶段右侧展示的是当前选中页的 research 内容，而不是 PPT 成稿。</p>
      </div>
    </div>
  );
}

function SlideCanvas({
  context,
  polished,
}: {
  context: SlideContext;
  polished: boolean;
}) {
  return (
    <div className={`preview-canvas-frame ${polished ? "preview-canvas-frame-polished" : ""}`}>
      <div className="artboard-wrapper">
        <div className="artboard">
          <div className="artboard-title">
            <span className="title-marker" />
            <div className="title-copy">
              <h2>{context.title}</h2>
            </div>
            <div className="title-meta">
              {`Page ${context.pageNo.toString().padStart(2, "0")}`}
            </div>
          </div>

          <div className="artboard-grid">
            <section className="art-card">
              <div className="art-card-head">
                <h3>核心观点</h3>
                <span className="blue-tag">{context.section}</span>
              </div>
              <p className="canvas-copy">{context.keyMessage}</p>
              <div className="status-strip">{context.type}</div>
            </section>

            <section className="art-card">
              <div className="art-card-head">
                <h3>支撑要点</h3>
                <span className="card-subtitle">Research Facts</span>
              </div>
              <ul className="bullet-list">
                {context.facts.slice(0, 4).map((fact) => (
                  <li key={fact}>{fact}</li>
                ))}
              </ul>
            </section>

            <section className="art-card">
              <div className="art-card-head">
                <h3>页面结构</h3>
              </div>
              <div className="loop-layout">
                <div className="loop-circle">{context.pageNo}</div>
                <ol className="number-list">
                  <li>{`受众：${context.audience}`}</li>
                  <li>{`场景：${context.scenario}`}</li>
                  <li>{`风格：${context.style}`}</li>
                </ol>
              </div>
              <div className="status-strip status-strip-soft">{`本页类型：${context.type}`}</div>
            </section>

            <section className="art-card">
              <div className="art-card-head">
                <h3>引用来源</h3>
                <span className="card-subtitle">Sources</span>
              </div>
              <div className="integrations-box integrations-box-sources">
                {context.citations.length ? (
                  context.citations.slice(0, 3).map((citation) => (
                    <span key={citation.url}>{citation.title}</span>
                  ))
                ) : (
                  <span>暂无真实外部引用</span>
                )}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}

function StageThumbnail({
  stage,
  context,
}: {
  stage: StageView;
  context: SlideContext;
}) {
  return (
    <div className="slide-thumb-canvas">
      <div className="slide-thumb-title">{context.title}</div>

      {stage === "search" ? (
        <div className="slide-thumb-search">
          <div className="slide-thumb-line" />
          <div className="slide-thumb-line short" />
          <div className="slide-thumb-grid">
            <span />
            <span />
          </div>
        </div>
      ) : null}

      {stage === "draft" ? (
        <div className="slide-thumb-draft">
          <div className="slide-thumb-line" />
          <div className="slide-thumb-line short" />
          <div className="slide-thumb-copy">{context.keyMessage}</div>
        </div>
      ) : null}

      {stage === "design" ? (
        <div className="slide-thumb-design">
          <div className="slide-thumb-design-grid">
            <span />
            <span />
            <span />
            <span />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function buildSlideContext(
  project: Project | null,
  slide: OutlineSlide | null,
  brief: RequirementBrief | null,
  research: ResearchPack | null
): SlideContext {
  const relatedTopics = selectRelatedTopics(slide, research?.topics ?? []);
  const facts = dedupeStrings(
    [
      slide?.key_message,
      brief?.goal,
      ...relatedTopics.flatMap((topic) => topic.facts),
      project ? `受众：${project.config.audience}` : undefined,
      project ? `场景：${project.config.scenario}` : undefined,
      project ? `风格：${project.config.style_pref}` : undefined,
    ].filter(Boolean) as string[]
  ).slice(0, 6);

  return {
    title: slide?.title ?? project?.title ?? DEFAULT_TITLE,
    pageNo: slide?.order_no ?? 1,
    section: slide?.section ?? "未生成",
    type: slide?.type ?? "draft",
    keyMessage: slide?.key_message ?? brief?.goal ?? "尚未生成当前页面内容。",
    audience: project?.config.audience ?? "未定义",
    scenario: project?.config.scenario ?? "未定义",
    style: project?.config.style_pref ?? "未定义",
    facts,
    citations: relatedTopics.flatMap((topic) => topic.citations).slice(0, 4),
  };
}

function selectRelatedTopics(
  slide: OutlineSlide | null,
  topics: ResearchTopic[]
): ResearchTopic[] {
  if (!slide || !topics.length) {
    return [];
  }

  const tokens = tokenize(`${slide.title} ${slide.key_message} ${slide.section}`);
  const scored = topics
    .map((topic, index) => ({
      topic,
      index,
      score: tokens.reduce((sum, token) => {
        const haystack = `${topic.name} ${topic.summary} ${topic.facts.join(" ")}`;
        return sum + (haystack.includes(token) ? 1 : 0);
      }, 0),
    }))
    .sort((left, right) => right.score - left.score || left.index - right.index);

  if (scored[0]?.score === 0) {
    return [topics[(slide.order_no - 1) % topics.length]];
  }

  return scored.filter((item) => item.score > 0).slice(0, 2).map((item) => item.topic);
}

function tokenize(text: string): string[] {
  return Array.from(
    new Set(
      text
        .split(/[\s，,。；;：:、()（）/]+/)
        .map((part) => part.trim())
        .filter((part) => part.length >= 2)
    )
  );
}

function dedupeStrings(values: string[]): string[] {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
}

function parsePrompt(prompt: string, files: File[]) {
  const pageMatch = prompt.match(/(\d{1,2})\s*页/);
  const pageLimit = pageMatch ? Number(pageMatch[1]) : 14;
  const stylePref = prompt.includes("商务")
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
      style_pref: stylePref,
      page_limit: Math.min(Math.max(pageLimit, 4), 20),
      research_enabled: true,
      narration_enabled: false,
    },
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
