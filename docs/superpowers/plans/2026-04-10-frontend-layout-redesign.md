# Frontend Layout Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重新设计编辑器页面布局：顶栏精简、左侧边栏横向阶段 tab + 缩略图列表、主内容区按阶段切换（搜索=引用主从、初稿/设计=全宽预览），并修复 Electron 窗口拖拽问题。

**Architecture:** 只修改 `App.tsx` 和 `styles.css` 两个文件。移除 `workspace-layout` 左右分栏，改为各阶段 workspace 组件直接铺满主内容区；`SearchWorkspace`、`DraftWorkspace`、`DesignWorkspace` 各自承担完整的布局职责；原有的 `SearchPreview`、`DraftPreview`、`SvgPreview` 组件功能合并进对应的 workspace 组件后删除。

**Tech Stack:** React 18, TypeScript, CSS Grid/Flexbox, Electron (`-webkit-app-region`)

**Spec:** `docs/superpowers/specs/2026-04-10-frontend-layout-redesign.md`

---

## File Map

| File | Changes |
|------|---------|
| `ppt-agent-desktop/src/renderer/styles.css` | Electron drag、body user-select、边栏宽度、横向 tab、新布局 class |
| `ppt-agent-desktop/src/renderer/App.tsx` | 顶栏精简、SearchWorkspace 重构、DraftWorkspace 重构、DesignWorkspace 重构、移除 Preview 组件、App 主布局简化 |

---

## Task 1: CSS — Electron 窗口拖拽 + body user-select

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/styles.css`

- [ ] **Step 1: 在 body 规则中加 `-webkit-user-select: none`**

在 `styles.css` 找到 `body {` 块（约第 34 行），在 `background:` 属性之后添加：

```css
body {
  min-height: 100vh;
  font-family: "Avenir Next", "PingFang SC", "Helvetica Neue", sans-serif;
  color: var(--text);
  background:
    radial-gradient(circle at top left, rgba(45, 108, 246, 0.08), transparent 24%),
    linear-gradient(180deg, #f7f9fc, #edf1f7 48%, #e9eef6);
  -webkit-user-select: none;
  user-select: none;
}
```

- [ ] **Step 2: 给 input 和 textarea 恢复文本选中**

找到 `button, input, textarea {` 块（约第 43 行），在其后添加新规则：

```css
input,
textarea {
  -webkit-user-select: text;
  user-select: text;
}
```

- [ ] **Step 3: 给 `.editor-topbar` 加 Electron 拖拽区域**

找到 `.editor-topbar {` 块（约第 237 行），在末尾加：

```css
.editor-topbar {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 18px;
  min-height: 76px;
  padding: 14px 22px;
  border-bottom: 1px solid rgba(216, 223, 235, 0.9);
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(18px);
  -webkit-app-region: drag;
}
```

- [ ] **Step 4: 给顶栏内所有按钮加 no-drag**

在 `.editor-topbar` 规则之后添加：

```css
.editor-topbar button,
.editor-topbar .export-dropdown {
  -webkit-app-region: no-drag;
}
```

- [ ] **Step 5: 验证**

在 Electron 中点住标题栏空白区域拖动窗口，窗口应随之移动；点击"返回输入"、"导出"按钮正常响应，不触发拖拽。

- [ ] **Step 6: 提交**

```bash
git add ppt-agent-desktop/src/renderer/styles.css
git commit -m "fix(frontend): fix Electron window drag and text selection"
```

---

## Task 2: CSS — 左侧边栏宽度 + 横向阶段 tab

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/styles.css`

- [ ] **Step 1: 边栏宽度从 148px 改为 220px**

找到 `.editor-body {` 块（约第 304 行），修改为：

```css
.editor-body {
  display: grid;
  grid-template-columns: 220px 1fr;
  min-height: 0;
}
```

- [ ] **Step 2: `.rail-stage-switch` 改为横向三等分**

找到 `.rail-stage-switch {` 块（约第 319 行），修改为：

```css
.rail-stage-switch {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 4px;
  padding: 4px;
  border-radius: 20px;
  background: rgba(236, 241, 248, 0.96);
}
```

- [ ] **Step 3: 移除 `.rail-stage-switch .stage-tab` 的 `width: 100%`**

找到 `.rail-stage-switch .stage-tab {` 块（约第 327 行），修改为：

```css
.rail-stage-switch .stage-tab {
  min-height: 34px;
  padding: 0 8px;
  font-size: 13px;
}
```

- [ ] **Step 4: 验证**

Electron 中切换到编辑器视图，确认左侧边栏变宽（220px），三个阶段 tab 横向排列并均分宽度，激活状态样式正常。

- [ ] **Step 5: 提交**

```bash
git add ppt-agent-desktop/src/renderer/styles.css
git commit -m "feat(frontend): widen sidebar and make stage tabs horizontal"
```

---

## Task 3: CSS — 新增布局 class

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/styles.css`

- [ ] **Step 1: 在文件末尾（`@media` 块之前）添加以下新 class**

```css
/* ── Search stage: citation master-detail ── */
.search-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 0;
  min-height: 0;
  overflow: hidden;
  border-radius: 28px;
  border: 1px solid rgba(216, 223, 235, 0.92);
  background: rgba(255, 255, 255, 0.8);
  box-shadow: var(--shadow-soft);
}

.citation-list {
  display: grid;
  align-content: start;
  gap: 6px;
  padding: 16px 12px;
  overflow-y: auto;
  border-right: 1px solid rgba(216, 223, 235, 0.82);
  background: rgba(255, 255, 255, 0.56);
}

.citation-list-item {
  display: grid;
  gap: 3px;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: 14px;
  cursor: pointer;
  text-align: left;
  background: transparent;
  color: var(--text);
  transition: background 180ms ease, border-color 180ms ease;
}

.citation-list-item:hover {
  background: var(--surface-muted);
}

.citation-list-item-active {
  background: var(--blue-soft);
  border-color: rgba(45, 108, 246, 0.2);
}

.citation-list-item strong {
  font-size: 13px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.citation-list-item span {
  font-size: 11px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.citation-detail {
  display: grid;
  align-content: start;
  gap: 14px;
  padding: 20px 22px;
  overflow-y: auto;
}

.citation-detail-title {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.3;
  margin: 0;
}

.citation-detail-url {
  display: block;
  font-size: 12px;
  color: var(--blue);
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.citation-detail-url:hover {
  text-decoration: underline;
}

.citation-detail-snippet {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.citation-empty {
  grid-column: 1 / -1;
  display: grid;
  place-items: center;
  min-height: 200px;
  color: var(--muted);
}

/* ── Draft / Design stage: full-width preview ── */
.stage-preview-shell {
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 14px;
  min-height: 0;
}

.stage-preview-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stage-preview-frame {
  display: grid;
  place-items: center;
  min-height: 0;
  padding: 24px;
  border-radius: 28px;
  border: 1px solid rgba(216, 223, 235, 0.92);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(247, 249, 253, 0.94)),
    linear-gradient(180deg, rgba(45, 108, 246, 0.06), transparent 18%);
  box-shadow: var(--shadow-soft);
  overflow: auto;
  position: relative;
}

/* ── Design stage: floating action bar ── */
.design-action-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

/* ── Design stage: review panel below SVG ── */
.review-panel {
  padding: 16px 20px;
  border: 1px solid rgba(216, 223, 235, 0.92);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.9);
}

.review-panel-warning {
  border-color: #f6ad55;
  background: #fffaf0;
}
```

- [ ] **Step 2: 更新 `editor-main` 让它不再有固定的 grid rows**

找到 `.editor-main {` 块（约第 485 行），修改为：

```css
.editor-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
```

- [ ] **Step 3: 提交**

```bash
git add ppt-agent-desktop/src/renderer/styles.css
git commit -m "feat(frontend): add new layout CSS classes for stage views"
```

---

## Task 4: Topbar — 移除"预览" pill 和"放映"按钮

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/App.tsx:621-673`

- [ ] **Step 1: 找到顶栏 JSX，替换 toolbar-center 和 toolbar-right**

当前顶栏 JSX（约第 623-673 行）：

```tsx
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
    <div className="export-dropdown" style={{ position: "relative" }}>
      ...
    </div>
  </div>
</header>
```

替换为（保留 export-dropdown 原有内容不变）：

```tsx
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
```

- [ ] **Step 2: 验证**

顶栏只剩"返回输入"、标题、"导出 ▾"，无"预览" pill，无"放映"按钮。

- [ ] **Step 3: 提交**

```bash
git add ppt-agent-desktop/src/renderer/App.tsx
git commit -m "feat(frontend): simplify topbar - remove preview pill and slideshow button"
```

---

## Task 5: SearchWorkspace — 引用主从布局

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/App.tsx:819-891`

- [ ] **Step 1: 替换整个 `SearchWorkspace` 函数**

找到 `function SearchWorkspace({` （约第 819 行），将整个函数替换为：

```tsx
function SearchWorkspace({
  page,
}: {
  page: SearchPage | null;
  research: ResearchPack | null;
}) {
  const [selectedIdx, setSelectedIdx] = useState(0);

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
```

- [ ] **Step 2: 验证**

切换到搜索阶段，左列显示当前幻灯片的引用来源列表（标题 + URL），点击任意一条，右列更新为该来源的详情。

- [ ] **Step 3: 提交**

```bash
git add ppt-agent-desktop/src/renderer/App.tsx
git commit -m "feat(frontend): redesign SearchWorkspace as citation master-detail"
```

---

## Task 6: DraftWorkspace — 全宽 artboard 预览

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/App.tsx:893-1068`

- [ ] **Step 1: 替换整个 `DraftWorkspace` 函数**

找到 `function DraftWorkspace({`（约第 893 行），将整个函数替换为：

```tsx
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
                    <span className="blue-tag">{(page.blocks[index] as { kind?: string })?.kind ?? ""}</span>
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
```

- [ ] **Step 2: 验证**

切换到初稿阶段，主区显示全宽 artboard（标题 + blocks 卡片），顶部有"编辑/保存"按钮，点击"编辑"后 block 内容可编辑。

- [ ] **Step 3: 提交**

```bash
git add ppt-agent-desktop/src/renderer/App.tsx
git commit -m "feat(frontend): redesign DraftWorkspace as full-width artboard preview"
```

---

## Task 7: DesignWorkspace — 全宽 SVG 预览 + 浮动操作栏 + 检查面板

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/App.tsx:1070-1157`

- [ ] **Step 1: 替换整个 `DesignWorkspace` 函数**

找到 `function DesignWorkspace({`（约第 1070 行），将整个函数替换为：

```tsx
function DesignWorkspace({
  page,
  isRegenerating,
  onRegenerate,
  reviewPage,
  isReviewing,
  onRunReview,
}: {
  page: SvgSlidePage | null;
  planPage: SlidePlanPage | null;
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
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: reviewPage.issues.length ? 10 : 0 }}>
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
```

- [ ] **Step 2: 验证**

切换到设计稿阶段，SVG 全宽居中显示；"重新生成"和"检查"按钮在顶部操作栏；点击"检查"后检查结果出现在 SVG 下方。

- [ ] **Step 3: 提交**

```bash
git add ppt-agent-desktop/src/renderer/App.tsx
git commit -m "feat(frontend): redesign DesignWorkspace as full-width SVG preview with action bar"
```

---

## Task 8: App 主布局 — 移除 workspace-layout 分栏

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/App.tsx:742-814`

- [ ] **Step 1: 找到 `editor-main` 内部的 JSX，替换整个 `workspace-layout` 块**

当前约第 742-814 行：

```tsx
<main className="editor-main">
  <section className="workspace-layout">
    <div className="workspace-panel workspace-panel-content">
      {stage === "search" ? (
        <SearchWorkspace page={selectedSearchPage} research={workspace.research} />
      ) : null}
      {stage === "draft" ? (
        <DraftWorkspace ... />
      ) : null}
      {stage === "design" ? (
        <DesignWorkspace ... />
      ) : null}
    </div>

    <div className="workspace-panel workspace-panel-preview">
      <div className="preview-header">...</div>
      {stage === "search" ? <SearchPreview page={selectedSearchPage} /> : null}
      {stage === "draft" ? <DraftPreview ... /> : null}
      {stage === "design" ? <SvgPreview page={selectedSvgPage} /> : null}
    </div>
  </section>

  {workspace.error ? <div className="error-banner">{workspace.error}</div> : null}
</main>
```

替换为（各 workspace 组件直接铺满 main 区域）：

```tsx
<main className="editor-main">
  {stage === "search" ? (
    <SearchWorkspace page={selectedSearchPage} research={workspace.research} />
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
      planPage={selectedPlanPage}
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
```

- [ ] **Step 2: 验证整体布局**

- 搜索阶段：左侧缩略图，主区引用主从两列
- 初稿阶段：左侧缩略图，主区全宽 artboard
- 设计稿阶段：左侧缩略图，主区全宽 SVG + 检查面板

- [ ] **Step 3: 提交**

```bash
git add ppt-agent-desktop/src/renderer/App.tsx
git commit -m "feat(frontend): remove workspace split, stages render full-width"
```

---

## Task 9: 清理废弃组件

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/App.tsx`

- [ ] **Step 1: 删除 `SearchPreview` 函数**

找到 `function SearchPreview({`（约第 1159 行），删除整个函数（包含 `}`）。

- [ ] **Step 2: 删除 `DraftPreview` 函数**

找到 `function DraftPreview({`（约第 1187 行），删除整个函数。

- [ ] **Step 3: 删除 `SvgPreview` 函数**

找到 `function SvgPreview({`（约第 1234 行），删除整个函数。

- [ ] **Step 4: 检查 TypeScript 编译无报错**

```bash
cd /Users/zzp/project/ppt-agent/ppt-agent-desktop
/Users/zzp/sdk/node/node-v24.13.0-darwin-arm64/bin/npx tsc --noEmit
```

预期：无报错输出。如有报错，按提示修复未使用的 import 或类型引用。

- [ ] **Step 5: 清理 CSS 废弃 class（可选）**

以下 class 在新布局中不再使用，可从 `styles.css` 中删除：
- `.workspace-layout`
- `.workspace-panel`
- `.workspace-panel-content`
- `.workspace-panel-preview`
- `.preview-header`
- `.research-preview-card`
- `.research-preview-frame`
- `.research-preview-page-no`
- `.research-preview-title`
- `.research-preview-copy`
- `.research-preview-list`
- `.research-preview-fact`
- `.research-preview-loading`
- `.research-preview-footer`
- `.deck-list-preview`
- `.deck-list-item`
- `.deck-list-item-active`

- [ ] **Step 6: 提交**

```bash
git add ppt-agent-desktop/src/renderer/App.tsx ppt-agent-desktop/src/renderer/styles.css
git commit -m "chore(frontend): remove unused Preview components and deprecated CSS"
```

---

## Self-Review Checklist

- [x] Electron 拖拽修复 → Task 1
- [x] body user-select + input 恢复 → Task 1
- [x] 顶栏精简（去 预览 pill、放映按钮）→ Task 4
- [x] 边栏宽度 220px → Task 2
- [x] 阶段 tab 横向三等分 → Task 2
- [x] 搜索阶段引用主从布局 → Task 5
- [x] 初稿阶段全宽 artboard → Task 6
- [x] 设计阶段全宽 SVG + 浮动操作栏 + 检查面板 → Task 7
- [x] 移除 workspace-layout 分栏 → Task 8
- [x] 清理废弃组件 → Task 9
