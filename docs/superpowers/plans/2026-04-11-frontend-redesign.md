# Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign ppt-agent-desktop's renderer into a SANDUN-inspired three-column layout with project history sidebar, welcome intake view, and right-side AI chat panel.

**Architecture:** The entire renderer lives in `App.tsx` (one large file, existing pattern preserved). New CSS classes are added to `styles.css`. No new files are created. The chat panel is frontend-only state — it displays progress messages from existing API calls and lets the user trigger regeneration commands via keyword matching.

**Tech Stack:** React 18, TypeScript, plain CSS (existing tokens), Electron renderer

---

## File Map

| File | What Changes |
|------|-------------|
| `ppt-agent-desktop/src/renderer/styles.css` | Add layout classes: `.app-shell`, `.app-sidebar`, `.intake-main`, `.chat-panel`, `.chat-messages`, `.chat-bubble`, `.chat-input-area`, `.project-item`, `.recent-projects`, `.welcome-heading` |
| `ppt-agent-desktop/src/renderer/App.tsx` | Add `chatMessages` + `chatInput` state; add `Sidebar`, `ChatPanel` components; refactor intake JSX; refactor editor JSX (stage tabs → topbar, add ChatPanel column) |

---

## Task 1: Add CSS layout classes

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/styles.css` (append at end)

- [ ] **Step 1: Append the new layout CSS to styles.css**

Add the following block at the very end of `styles.css`:

```css
/* ── Redesign: three-column app shell ── */
.app-shell {
  display: flex;
  min-height: 100vh;
}

/* ── Redesign: shared sidebar ── */
.app-sidebar {
  flex-shrink: 0;
  width: 220px;
  display: flex;
  flex-direction: column;
  gap: 0;
  border-right: 1px solid rgba(216, 223, 235, 0.82);
  background: rgba(255, 255, 255, 0.56);
  backdrop-filter: blur(18px);
  -webkit-app-region: drag;
}

.app-sidebar button,
.app-sidebar input {
  -webkit-app-region: no-drag;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 20px 16px 12px;
  font-size: 15px;
  font-weight: 800;
  color: var(--blue);
  letter-spacing: 0.08em;
}

.sidebar-new-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 10px 4px;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.9);
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: background 150ms ease, transform 150ms ease;
}

.sidebar-new-btn:hover {
  background: var(--blue-soft);
  color: var(--blue);
  transform: translateY(-1px);
}

.sidebar-section-label {
  padding: 10px 16px 4px;
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.project-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin: 0 6px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
  text-align: left;
  transition: background 150ms ease, border-color 150ms ease;
  overflow: hidden;
}

.project-item:hover {
  background: var(--surface-muted);
}

.project-item-active {
  background: var(--blue-soft);
  border-color: rgba(45, 108, 246, 0.18);
  color: var(--blue);
  box-shadow: inset 3px 0 0 var(--blue);
}

.project-item-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}

.project-item-badge {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--surface-muted);
  color: var(--muted);
}

.project-item-badge-blue {
  background: var(--blue-soft);
  color: var(--blue);
}

.sidebar-empty {
  padding: 20px 16px;
  font-size: 12px;
  color: var(--muted);
  text-align: center;
}

.sidebar-spacer {
  flex: 1;
}

.sidebar-bottom {
  padding: 12px 16px;
  border-top: 1px solid rgba(216, 223, 235, 0.7);
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ── Redesign: intake main area ── */
.intake-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 40px 48px;
  min-height: 100vh;
  gap: 0;
  -webkit-app-region: drag;
}

.intake-main button,
.intake-main input,
.intake-main textarea {
  -webkit-app-region: no-drag;
}

.welcome-heading {
  font-size: 52px;
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: -0.02em;
  color: var(--text);
  margin: 0 0 8px;
  text-align: center;
}

.welcome-subtitle {
  font-size: 15px;
  color: var(--muted);
  margin: 0 0 32px;
  text-align: center;
}

.intake-box {
  width: min(680px, 100%);
  padding: 18px;
  border: 1px solid rgba(216, 223, 235, 0.9);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(24px);
  box-shadow: var(--shadow-strong);
  display: grid;
  gap: 12px;
}

.intake-box textarea {
  width: 100%;
  min-height: 120px;
  padding: 16px;
  border: 0;
  border-radius: 16px;
  resize: vertical;
  color: var(--text);
  line-height: 1.75;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(244, 247, 252, 0.98));
  box-shadow: inset 0 0 0 1px rgba(216, 223, 235, 0.92);
}

.intake-box textarea:focus {
  outline: none;
  box-shadow: inset 0 0 0 1px rgba(45, 108, 246, 0.28);
}

.intake-box-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.intake-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.intake-chip {
  padding: 7px 16px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.9);
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
  transition: background 150ms ease, border-color 150ms ease, transform 150ms ease;
}

.intake-chip:hover {
  background: var(--blue-soft);
  border-color: rgba(45, 108, 246, 0.28);
  color: var(--blue);
  transform: translateY(-1px);
}

.recent-projects {
  margin-top: 40px;
  width: min(680px, 100%);
}

.recent-projects-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 12px;
}

.recent-projects-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.recent-project-card {
  padding: 14px;
  border: 1px solid rgba(216, 223, 235, 0.92);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(12px);
  cursor: pointer;
  text-align: left;
  transition: transform 150ms ease, box-shadow 150ms ease;
}

.recent-project-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-soft);
}

.recent-project-card-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 6px;
}

.recent-project-card-meta {
  font-size: 11px;
  color: var(--muted);
}

/* ── Redesign: editor topbar with stage tabs ── */
.editor-topbar-redesign {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
  min-height: 64px;
  padding: 0 20px;
  border-bottom: 1px solid rgba(216, 223, 235, 0.9);
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(18px);
  -webkit-app-region: drag;
  flex-shrink: 0;
}

.editor-topbar-redesign button,
.editor-topbar-redesign .export-dropdown {
  -webkit-app-region: no-drag;
}

.editor-shell-mac .editor-topbar-redesign {
  padding-left: 96px;
}

.editor-body-redesign {
  display: grid;
  grid-template-columns: 220px 1fr 320px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* ── Redesign: chat panel ── */
.chat-panel {
  display: flex;
  flex-direction: column;
  border-left: 1px solid rgba(216, 223, 235, 0.82);
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(18px);
  min-height: 0;
}

.chat-panel-header {
  padding: 14px 16px 10px;
  border-bottom: 1px solid rgba(216, 223, 235, 0.7);
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-panel-stage-badge {
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--blue-soft);
  color: var(--blue);
  font-size: 11px;
  font-weight: 700;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 14px 14px 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
}

.chat-bubble {
  max-width: 90%;
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 13px;
  line-height: 1.55;
}

.chat-bubble-ai {
  align-self: flex-start;
  background: var(--surface-muted);
  border-bottom-left-radius: 4px;
  color: var(--text);
}

.chat-bubble-user {
  align-self: flex-end;
  background: var(--blue);
  border-bottom-right-radius: 4px;
  color: #fff;
}

.chat-bubble-time {
  font-size: 10px;
  color: var(--muted);
  margin-top: 2px;
  padding: 0 2px;
}

.chat-input-area {
  padding: 12px;
  border-top: 1px solid rgba(216, 223, 235, 0.7);
  display: grid;
  gap: 8px;
}

.chat-input-area textarea {
  width: 100%;
  min-height: 64px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 14px;
  resize: none;
  background: var(--surface-soft);
  color: var(--text);
  font-size: 13px;
  line-height: 1.55;
  -webkit-user-select: text;
  user-select: text;
}

.chat-input-area textarea:focus {
  outline: none;
  box-shadow: inset 0 0 0 1px rgba(45, 108, 246, 0.28);
}

.chat-input-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.chat-hint {
  font-size: 11px;
  color: var(--muted);
}
```

- [ ] **Step 2: Verify the CSS has no syntax errors**

Open `styles.css` and scan the end of the file — confirm the new block starts with `/* ── Redesign: three-column app shell ── */` and all braces are balanced.

- [ ] **Step 3: Commit**

```bash
cd /Users/zzp/project/ppt-agent/ppt-agent-desktop
git add src/renderer/styles.css
git commit -m "style: add redesign layout CSS classes"
```

---

## Task 2: Add chat state and Sidebar component

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/App.tsx`

- [ ] **Step 1: Add ChatMessage type and new state at the top of App()**

Find the existing state declarations block (lines starting with `const [health,` etc.) and add two new state variables right after `const [exportMenuOpen, setExportMenuOpen] = useState(false);`:

```tsx
type ChatMessage = {
  id: string;
  role: "ai" | "user";
  text: string;
  time: string;
};

// inside App() function, after exportMenuOpen state:
const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
const [chatInput, setChatInput] = useState("");
const chatEndRef = useRef<HTMLDivElement | null>(null);
```

Note: the `type ChatMessage` declaration goes at the top of the file, alongside the other type declarations (after `type SlideReference`).

- [ ] **Step 2: Add addChatMessage helper inside App()**

Add this function after `handleReturnToIntake`:

```tsx
function addChatMessage(role: "ai" | "user", text: string) {
  const now = new Date();
  const time = `${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}`;
  setChatMessages((prev) => [
    ...prev,
    { id: `${Date.now()}-${Math.random()}`, role, text, time },
  ]);
  setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
}
```

- [ ] **Step 3: Add AI progress messages to ensureStageArtifacts()**

In `ensureStageArtifacts`, add `addChatMessage` calls at key points. Replace the try block opening lines:

```tsx
// At the very start of the try block inside ensureStageArtifacts:
addChatMessage("ai", `正在准备${stageLabels[nextStage]}阶段...`);
```

And at the end of startTransition callback (after `setStage(nextStage)`), add:

```tsx
addChatMessage("ai", `${stageLabels[nextStage]}阶段已就绪，共 ${orderedSlides.length} 页。`);
```

And in the catch block of `ensureStageArtifacts`:

```tsx
addChatMessage("ai", `生成失败：${message}`);
```

- [ ] **Step 4: Add AI message when a SVG page regenerates**

In `handleRegenerateSvgPage`, inside the try block before the API call:

```tsx
addChatMessage("ai", `正在重新生成第 ${workspace.svgArtifact?.pages.find(p => p.slide_id === slideId)?.order_no ?? "?"} 页设计稿...`);
```

After `startTransition` completes (end of the try block):

```tsx
addChatMessage("ai", "设计稿页面已更新。");
```

- [ ] **Step 5: Add AI message when project loads**

In `loadProjectArtifacts`, at the end of the successful `startTransition` call (after `isBusy: false`):

```tsx
addChatMessage("ai", `项目"${project.title}"已加载，可在此输入修改指令。`);
```

- [ ] **Step 6: Add Sidebar component (below reorderSlides function)**

Add this new component at the bottom of `App.tsx`, after `reorderSlides`:

```tsx
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
```

- [ ] **Step 7: Commit**

```bash
cd /Users/zzp/project/ppt-agent/ppt-agent-desktop
git add src/renderer/App.tsx
git commit -m "feat: add chat state, progress messages, and Sidebar component"
```

---

## Task 3: Redesign Intake page

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/App.tsx`

- [ ] **Step 1: Replace the intake page JSX**

Find the entire `if (pageView === "intake") { return ( ... ); }` block (currently lines ~544–603) and replace it with:

```tsx
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
          setWorkspace((current) => ({ ...current, selectedProjectId: id }));
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
```

- [ ] **Step 2: Visually verify intake page structure**

Run the app with `pnpm dev` (or the project's dev command). Check:
- Left sidebar shows brand name and "新建项目" button
- Main area shows greeting + subtitle + input box + chips
- If projects exist: recent project cards appear below chips

```bash
cd /Users/zzp/project/ppt-agent/ppt-agent-desktop
/Users/zzp/sdk/node/node-v24.13.0-darwin-arm64/bin/pnpm dev
```

- [ ] **Step 3: Commit**

```bash
cd /Users/zzp/project/ppt-agent/ppt-agent-desktop
git add src/renderer/App.tsx
git commit -m "feat: redesign intake page with sidebar and welcome area"
```

---

## Task 4: Add ChatPanel component

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/App.tsx`

- [ ] **Step 1: Add ChatPanel component (after Sidebar component)**

Add this component after the `Sidebar` function at the bottom of `App.tsx`:

```tsx
function ChatPanel({
  messages,
  input,
  isBusy,
  stage,
  chatEndRef,
  onInputChange,
  onSubmit,
}: {
  messages: ChatMessage[];
  input: string;
  isBusy: boolean;
  stage: StageView;
  chatEndRef: React.RefObject<HTMLDivElement>;
  onInputChange: (v: string) => void;
  onSubmit: () => void;
}) {
  const stageLabel: Record<StageView, string> = {
    search: "搜索",
    draft: "初稿",
    design: "设计稿",
  };

  return (
    <div className="chat-panel">
      <div className="chat-panel-header">
        AI 助手
        <span className="chat-panel-stage-badge">{stageLabel[stage]}</span>
      </div>

      {messages.length === 0 ? (
        <div className="chat-empty">
          <span style={{ fontSize: 28 }}>💬</span>
          <span>生成完成后，可在这里输入修改指令</span>
        </div>
      ) : (
        <div className="chat-messages">
          {messages.map((msg) => (
            <div key={msg.id}>
              <div className={`chat-bubble chat-bubble-${msg.role}`}>{msg.text}</div>
              <div
                className="chat-bubble-time"
                style={{ textAlign: msg.role === "user" ? "right" : "left" }}
              >
                {msg.time}
              </div>
            </div>
          ))}
          {isBusy ? (
            <div className="chat-bubble chat-bubble-ai">处理中...</div>
          ) : null}
          <div ref={chatEndRef} />
        </div>
      )}

      <div className="chat-input-area">
        <textarea
          placeholder="输入修改需求..."
          value={input}
          disabled={isBusy}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSubmit();
            }
          }}
        />
        <div className="chat-input-row">
          <span className="chat-hint">Enter 发送，Shift+Enter 换行</span>
          <button
            className="submit-button"
            disabled={isBusy || !input.trim()}
            onClick={onSubmit}
            style={{ minHeight: 34, padding: "0 14px", fontSize: 13 }}
            type="button"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add handleChatSubmit inside App()**

Add this function after `addChatMessage`:

```tsx
function handleChatSubmit() {
  const text = chatInput.trim();
  if (!text || !workspace.selectedProjectId) return;
  addChatMessage("user", text);
  setChatInput("");

  const lower = text.toLowerCase();
  if (lower.includes("设计稿") || lower.includes("design")) {
    void ensureStageArtifacts("design");
  } else if (lower.includes("初稿") || lower.includes("draft")) {
    void ensureStageArtifacts("draft");
  } else if (lower.includes("搜索") || lower.includes("search")) {
    void ensureStageArtifacts("search");
  } else if (lower.includes("重新生成") && selectedSlideId) {
    void handleRegenerateSvgPage(selectedSlideId);
  } else if (lower.includes("检查") || lower.includes("review")) {
    void handleRunReview();
  } else {
    addChatMessage("ai", "收到。目前支持的指令：「进入设计稿」「进入初稿」「重新生成」「检查」。");
  }
}
```

- [ ] **Step 3: Commit**

```bash
cd /Users/zzp/project/ppt-agent/ppt-agent-desktop
git add src/renderer/App.tsx
git commit -m "feat: add ChatPanel component and handleChatSubmit"
```

---

## Task 5: Redesign Editor page layout

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/App.tsx`

- [ ] **Step 1: Replace the editor page JSX**

Find the entire `return (` block for the editor (currently starting at `return ( <div className={\`editor-shell ...`) and replace it with:

```tsx
return (
  <div className={`editor-shell app-shell flex-column ${isMac ? "editor-shell-mac" : ""}`}>
    {/* Top navigation bar */}
    <header className="editor-topbar-redesign">
      <div className="toolbar-left">
        <button className="back-button" onClick={handleReturnToIntake} type="button">
          ← 返回
        </button>
      </div>

      <div className="toolbar-center">
        <strong style={{ fontSize: 15, maxWidth: 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {selectedProject?.title ?? DEFAULT_TITLE}
        </strong>
        <div className="stage-tabs">
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

    {/* Three-column body */}
    <div className="editor-body-redesign">
      {/* Left: slide rail (no stage-switch, moved to topbar) */}
      <aside className="slide-rail">
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
              onDragOver={(e) => e.preventDefault()}
              onDragStart={() => setDraggedSlideId(slide.slide_id)}
              onDrop={() => void handleDrop(slide.slide_id)}
              type="button"
            >
              <span className="slide-thumb-index">{slide.order_no}</span>
              <StageThumbnail
                draftPage={workspace.slidePlan?.pages.find((p) => p.slide_id === slide.slide_id)}
                outlineSlide={workspace.outline?.slides.find((s) => s.slide_id === slide.slide_id)}
                searchPage={workspace.searchPages?.pages.find((p) => p.slide_id === slide.slide_id)}
                stage={stage}
                svgPage={workspace.svgArtifact?.pages.find((p) => p.slide_id === slide.slide_id)}
                title={slide.title}
                regeneratingSlideId={workspace.regeneratingSlideId}
                reviewPage={workspace.reviewArtifact?.pages.find((p) => p.slide_id === slide.slide_id)}
              />
            </button>
          ))}
        </div>
      </aside>

      {/* Center: main stage content */}
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
              workspace.reviewArtifact?.pages.find((p) => p.slide_id === selectedSlideId) ?? null
            }
            isReviewing={workspace.isReviewing}
            onRunReview={() => void handleRunReview()}
          />
        ) : null}

        {workspace.error ? <div className="error-banner">{workspace.error}</div> : null}
      </main>

      {/* Right: AI chat panel */}
      <ChatPanel
        messages={chatMessages}
        input={chatInput}
        isBusy={workspace.isBusy}
        stage={stage}
        chatEndRef={chatEndRef}
        onInputChange={setChatInput}
        onSubmit={handleChatSubmit}
      />
    </div>
  </div>
);
```

- [ ] **Step 2: Add `flex-column` CSS utility to styles.css**

Append to the very end of `styles.css`:

```css
/* utility */
.flex-column {
  display: flex;
  flex-direction: column;
}
```

- [ ] **Step 3: Verify editor layout**

Start the dev server and open the editor by submitting a prompt or clicking a project:
- Top bar: ← 返回 | title + stage tabs | 导出▾
- Left: slide thumbnails with no stage-switch widget
- Center: stage content (search/draft/design)
- Right: chat panel with header "AI 助手" + stage badge

```bash
cd /Users/zzp/project/ppt-agent/ppt-agent-desktop
/Users/zzp/sdk/node/node-v24.13.0-darwin-arm64/bin/pnpm dev
```

- [ ] **Step 4: Commit**

```bash
cd /Users/zzp/project/ppt-agent/ppt-agent-desktop
git add src/renderer/App.tsx src/renderer/styles.css
git commit -m "feat: redesign editor layout — three-column with ChatPanel"
```

---

## Task 6: Polish and edge cases

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/styles.css`
- Modify: `ppt-agent-desktop/src/renderer/App.tsx`

- [ ] **Step 1: Fix intake page height on Mac (traffic lights)**

The `.app-sidebar` needs extra top padding on Mac to avoid overlapping with traffic lights. In the intake JSX, pass `isMac` to Sidebar and add a conditional class:

In `Sidebar` component props, add `isMac?: boolean`:

```tsx
function Sidebar({
  projects,
  selectedProjectId,
  onSelectProject,
  onNewProject,
  isMac,
}: {
  projects: Project[];
  selectedProjectId: string | null;
  onSelectProject: (id: string) => void;
  onNewProject: () => void;
  isMac?: boolean;
}) {
  // ...existing body unchanged...
  return (
    <aside className={`app-sidebar${isMac ? " app-sidebar-mac" : ""}`}>
```

Add CSS for Mac sidebar:

```css
.app-sidebar-mac .sidebar-brand {
  padding-top: 44px;
}
```

Pass `isMac={isMac}` to both `<Sidebar />` usages (intake and editor).

- [ ] **Step 2: Make editor-body-redesign fill remaining height**

The editor body must fill the space below the topbar. In `styles.css`, update `.editor-body-redesign`:

```css
.editor-body-redesign {
  display: grid;
  grid-template-columns: 220px 1fr 320px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
```

And `.editor-shell` already has `min-height: 100vh`. The `app-shell flex-column` class on the editor shell ensures correct stacking.

- [ ] **Step 3: Ensure chat panel scrolls to bottom on new messages**

The `chatEndRef.current?.scrollIntoView` in `addChatMessage` handles this. Verify by opening the editor and switching stages — AI messages should appear and the panel should auto-scroll.

- [ ] **Step 4: Fix export-menu z-index**

The export dropdown can be obscured by the chat panel. Add to `styles.css`:

```css
.export-menu {
  z-index: 100;
}
```

- [ ] **Step 5: Final visual check**

Open the app. Verify these scenarios:
1. **Cold start (no projects):** Intake shows greeting + empty sidebar "暂无记录" + no recent projects grid
2. **After first project created:** Sidebar shows the new project highlighted; editor opens with three columns
3. **Stage switch:** Click 初稿/设计稿 tabs in topbar — chat panel shows "正在准备…" AI message
4. **Chat submit:** Type "重新生成" → chat bubble appears + slide regeneration starts
5. **Back button:** Returns to intake; sidebar still shows project list

- [ ] **Step 6: Commit**

```bash
cd /Users/zzp/project/ppt-agent/ppt-agent-desktop
git add src/renderer/App.tsx src/renderer/styles.css
git commit -m "fix: polish editor height, Mac sidebar padding, export menu z-index"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| Left sidebar — intake: project history | Task 2, 3 |
| Left sidebar — editor: slide thumbnails | Task 5 |
| Welcome heading with time-of-day greeting | Task 3 |
| Intake input box with attachment + submit | Task 3 |
| Quick-suggestion chips | Task 3 |
| Recent project cards grid | Task 3 |
| EditorTopbar with stage tabs | Task 5 |
| Back button in editor topbar | Task 5 |
| Remove rail-stage-switch from slide rail | Task 5 |
| ChatPanel — right 320px column | Task 4, 5 |
| ChatPanel — AI progress messages | Task 2 |
| ChatPanel — user input triggers API calls | Task 4 |
| ChatPanel — empty state message | Task 4 |
| ChatPanel — auto-scroll to bottom | Task 2, 6 |
| Preserve existing glassmorphism styles | All tasks (no CSS token changes) |
| Mac traffic light padding | Task 6 |

**No placeholders found.**

**Type consistency:** `ChatMessage` defined once in Task 2 Step 1, used identically in Tasks 2, 4, 5. `Sidebar` props defined in Task 2 Step 6, extended in Task 6 Step 1 with optional `isMac`.
