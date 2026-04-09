# DeckFlow 未完成功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按优先级补全 DeckFlow 的五个未完成功能：初稿块级编辑、设计稿单页重跑、SVG/PDF 导出、Tavily 联网搜索、Review Engine。

**Architecture:** 全部功能沿用现有后端文件存储（`save_artifact` / `load_artifact`）+ FastAPI 路由模式，前端沿用 `api.ts` + `types.ts` + `App.tsx` 的三层结构，不引入新的状态管理库。

**Tech Stack:** Python 3.13 / FastAPI / Pydantic / pytest / httpx（后端测试）；React 18 / TypeScript（前端）；cairosvg + pypdf（PDF 导出）；tavily-python（联网搜索）

---

## 文件变更总览

| 文件 | 变更类型 |
|------|---------|
| `ppt-agent/pyproject.toml` | 新增依赖 cairosvg、pypdf、tavily-python、pytest、httpx |
| `ppt-agent/src/ppt_agent/schemas/slide_plan.py` | 新增 `SlidePlanBlockUpdate`、`SlidePlanPageUpdateRequest` |
| `ppt-agent/src/ppt_agent/schemas/review.py` | 新建，定义 `ReviewIssue`、`ReviewPage`、`ReviewArtifact` |
| `ppt-agent/src/ppt_agent/services/project_service.py` | 新增 5 个 service 方法 |
| `ppt-agent/src/ppt_agent/api/routes/projects.py` | 新增 7 个路由 |
| `ppt-agent/src/ppt_agent/config.py` | 新增 `tavily_api_key` 字段 |
| `ppt-agent/src/ppt_agent/api/routes/health.py` | 新增 Tavily 健康状态 |
| `ppt-agent/tests/conftest.py` | 新建，pytest fixtures |
| `ppt-agent/tests/test_draft_edit.py` | 新建 |
| `ppt-agent/tests/test_svg_rerun.py` | 新建 |
| `ppt-agent/tests/test_export.py` | 新建 |
| `ppt-agent/tests/test_tavily.py` | 新建 |
| `ppt-agent/tests/test_review.py` | 新建 |
| `ppt-agent-desktop/src/renderer/types.ts` | 新增 `SlidePlanPageUpdateRequest`、`ReviewArtifact`、`ReviewPage`、`ReviewIssue` |
| `ppt-agent-desktop/src/renderer/services/api.ts` | 新增 5 个 API 方法 |
| `ppt-agent-desktop/src/renderer/App.tsx` | 更新 `DraftWorkspace`、`DraftPreview`、`DesignWorkspace` |

---

## Task 1: 搭建测试基础设施

**Files:**
- Modify: `ppt-agent/pyproject.toml`
- Create: `ppt-agent/tests/__init__.py`
- Create: `ppt-agent/tests/conftest.py`

- [ ] **Step 1: 添加测试依赖**

在 `ppt-agent/pyproject.toml` 的 `[project]` 段添加 optional dev 依赖：

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0,<9.0",
    "httpx>=0.28,<1.0",
    "pytest-anyio>=0.0.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: 安装测试依赖**

```bash
cd ppt-agent && uv add --dev pytest httpx
```

Expected: `uv.lock` 更新，`pytest` 可用

- [ ] **Step 3: 创建 `tests/__init__.py`**

```python
```

（空文件）

- [ ] **Step 4: 创建 `tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import os

from ppt_agent.api.app import create_app
from ppt_agent.config import get_settings, Settings
from ppt_agent.services.storage_repository import StorageRepository
from ppt_agent.services.project_service import ProjectService


@pytest.fixture
def tmp_storage(tmp_path: Path) -> Path:
    return tmp_path / "storage"


@pytest.fixture
def repository(tmp_storage: Path) -> StorageRepository:
    return StorageRepository(tmp_storage)


@pytest.fixture
def service(repository: StorageRepository) -> ProjectService:
    return ProjectService(repository)


@pytest.fixture
def client(tmp_storage: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PPT_AGENT_STORAGE_ROOT", str(tmp_storage))
    monkeypatch.setenv("PPT_AGENT_DATABASE_AUTO_CREATE", "false")
    get_settings.cache_clear()
    app = create_app()
    return TestClient(app)
```

- [ ] **Step 5: 验证测试基础可运行**

```bash
cd ppt-agent && uv run pytest tests/ -v
```

Expected: `no tests ran` 且无报错

- [ ] **Step 6: 提交**

```bash
git add ppt-agent/pyproject.toml ppt-agent/tests/
git commit -m "chore: add pytest test infrastructure"
```

---

## Task 2: 初稿编辑 — 后端 Schema

**Files:**
- Modify: `ppt-agent/src/ppt_agent/schemas/slide_plan.py`

- [ ] **Step 1: 在 `slide_plan.py` 末尾添加更新请求类型**

```python
class SlidePlanBlockUpdate(BaseModel):
    block_id: str
    title: str | None = None
    content: str | None = None
    emphasis: str | None = None


class SlidePlanPageUpdateRequest(BaseModel):
    title: str | None = None
    core_message: str | None = None
    visual_focus: str | None = None
    blocks: list[SlidePlanBlockUpdate] | None = None
```

- [ ] **Step 2: 验证导入无报错**

```bash
cd ppt-agent && uv run python -c "from ppt_agent.schemas.slide_plan import SlidePlanPageUpdateRequest; print('ok')"
```

Expected: `ok`

---

## Task 3: 初稿编辑 — 后端 Service + 测试

**Files:**
- Modify: `ppt-agent/src/ppt_agent/services/project_service.py`
- Create: `ppt-agent/tests/test_draft_edit.py`

- [ ] **Step 1: 写失败测试**

创建 `ppt-agent/tests/test_draft_edit.py`：

```python
import pytest
from datetime import UTC, datetime
from ppt_agent.schemas.project import ProjectCreateRequest, ProjectConfigPayload
from ppt_agent.schemas.slide_plan import (
    SlidePlanArtifact, SlidePlanPage, SlidePlanBlock,
    SlidePlanPageUpdateRequest, SlidePlanBlockUpdate,
)
from ppt_agent.services.storage_repository import StorageRepository
from ppt_agent.services.project_service import ProjectService


def make_project(service: ProjectService) -> str:
    project = service.create_project(ProjectCreateRequest(
        title="测试项目",
        topic="这是一个测试",
        config=ProjectConfigPayload(
            scenario="汇报", audience="团队", style_pref="简洁",
        ),
    ))
    return project.id


def seed_slide_plan(repository: StorageRepository, project_id: str) -> SlidePlanArtifact:
    artifact = SlidePlanArtifact(
        project_id=project_id,
        version=1,
        pages=[
            SlidePlanPage(
                slide_id=f"{project_id}_s1",
                order_no=1,
                title="封面",
                narrative_role="开场",
                core_message="核心消息",
                visual_focus="标题区",
                suggested_layout="cover",
                design_notes=[],
                blocks=[
                    SlidePlanBlock(
                        block_id="b1",
                        kind="text",
                        title="标题块",
                        content="原始内容",
                        words_budget=50,
                        emphasis="high",
                    )
                ],
            )
        ],
    )
    repository.save_artifact(project_id, "slide_plan", artifact.model_dump(mode="json"))
    return artifact


def test_update_slide_plan_page_title(service: ProjectService, repository: StorageRepository):
    project_id = make_project(service)
    seed_slide_plan(repository, project_id)

    updated = service.update_slide_plan_page(
        project_id,
        f"{project_id}_s1",
        SlidePlanPageUpdateRequest(title="新标题"),
    )

    assert updated.title == "新标题"
    assert updated.core_message == "核心消息"  # 未改的字段保持不变


def test_update_slide_plan_page_blocks(service: ProjectService, repository: StorageRepository):
    project_id = make_project(service)
    seed_slide_plan(repository, project_id)

    updated = service.update_slide_plan_page(
        project_id,
        f"{project_id}_s1",
        SlidePlanPageUpdateRequest(
            blocks=[SlidePlanBlockUpdate(block_id="b1", content="新内容")]
        ),
    )

    assert updated.blocks[0].content == "新内容"
    assert updated.blocks[0].title == "标题块"  # 未改字段保持不变


def test_update_slide_plan_page_persists(service: ProjectService, repository: StorageRepository):
    project_id = make_project(service)
    seed_slide_plan(repository, project_id)

    service.update_slide_plan_page(
        project_id,
        f"{project_id}_s1",
        SlidePlanPageUpdateRequest(title="持久化标题"),
    )

    reloaded = service.get_slide_plan(project_id)
    assert reloaded.pages[0].title == "持久化标题"
```

- [ ] **Step 2: 运行确认失败**

```bash
cd ppt-agent && uv run pytest tests/test_draft_edit.py -v
```

Expected: `AttributeError: 'ProjectService' object has no attribute 'update_slide_plan_page'`

- [ ] **Step 3: 在 `project_service.py` 中实现 `update_slide_plan_page`**

在 `get_slide_plan` 方法后添加：

```python
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
        updated_blocks = [
            block.model_copy(
                update={
                    k: v
                    for k, v in {
                        "title": block_map[block.block_id].title,
                        "content": block_map[block.block_id].content,
                        "emphasis": block_map[block.block_id].emphasis,
                    }.items()
                    if block.block_id in block_map and v is not None
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
```

同时在文件顶部的导入中补充：

```python
from ppt_agent.schemas.slide_plan import SlidePlanArtifact, SlidePlanBlock, SlidePlanPage, SlidePlanPageUpdateRequest
```

（将现有导入行替换，加入 `SlidePlanPageUpdateRequest`）

- [ ] **Step 4: 运行确认通过**

```bash
cd ppt-agent && uv run pytest tests/test_draft_edit.py -v
```

Expected: 3 个测试全部 PASS

- [ ] **Step 5: 提交**

```bash
git add ppt-agent/src/ppt_agent/schemas/slide_plan.py \
        ppt-agent/src/ppt_agent/services/project_service.py \
        ppt-agent/tests/test_draft_edit.py
git commit -m "feat(backend): add draft page edit service"
```

---

## Task 4: 初稿编辑 — 后端路由

**Files:**
- Modify: `ppt-agent/src/ppt_agent/api/routes/projects.py`

- [ ] **Step 1: 在 `projects.py` 末尾添加路由**

在现有最后一个路由后追加：

```python
@router.patch(
    "/{project_id}/slide-plan/pages/{slide_id}",
    response_model=SlidePlanPage,
)
def update_slide_plan_page(
    project_id: str,
    slide_id: str,
    payload: SlidePlanPageUpdateRequest,
) -> SlidePlanPage:
    service = get_project_service()
    try:
        return service.update_slide_plan_page(project_id, slide_id, payload)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
```

同时更新顶部 import，加入 `SlidePlanPage` 和 `SlidePlanPageUpdateRequest`：

```python
from ppt_agent.schemas.slide_plan import SlidePlanArtifact, SlidePlanPage, SlidePlanPageUpdateRequest
```

- [ ] **Step 2: 添加路由集成测试到 `test_draft_edit.py`**

在文件末尾追加：

```python
def test_patch_slide_plan_page_route(client, repository):
    # 先通过 intake 创建项目
    resp = client.post(
        "/api/projects/intake",
        data={"prompt": "测试项目，8页，科技风，团队汇报"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # 注入 slide_plan artifact
    seed_slide_plan(repository, project_id)

    # 调用 PATCH
    resp = client.patch(
        f"/api/projects/{project_id}/slide-plan/pages/{project_id}_s1",
        json={"title": "路由测试标题"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "路由测试标题"
```

- [ ] **Step 3: 运行测试**

```bash
cd ppt-agent && uv run pytest tests/test_draft_edit.py -v
```

Expected: 4 个测试全部 PASS

- [ ] **Step 4: 提交**

```bash
git add ppt-agent/src/ppt_agent/api/routes/projects.py \
        ppt-agent/tests/test_draft_edit.py
git commit -m "feat(backend): add PATCH slide-plan page route"
```

---

## Task 5: 初稿编辑 — 前端类型 + API

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/types.ts`
- Modify: `ppt-agent-desktop/src/renderer/services/api.ts`

- [ ] **Step 1: 在 `types.ts` 末尾添加类型**

```typescript
export type SlidePlanBlockUpdate = {
  block_id: string;
  title?: string;
  content?: string;
  emphasis?: "high" | "medium" | "low";
};

export type SlidePlanPageUpdateRequest = {
  title?: string;
  core_message?: string;
  visual_focus?: string;
  blocks?: SlidePlanBlockUpdate[];
};
```

- [ ] **Step 2: 在 `api.ts` 中添加 `updateSlidePlanPage`**

在 `reorderOutline` 后添加：

```typescript
updateSlidePlanPage: (
  projectId: string,
  slideId: string,
  payload: SlidePlanPageUpdateRequest
) =>
  request<SlidePlanPage>(
    `/api/projects/${projectId}/slide-plan/pages/${slideId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    }
  ),
```

同时更新 `api.ts` 顶部 import，加入 `SlidePlanPage` 和 `SlidePlanPageUpdateRequest`：

```typescript
import type {
  HealthResponse,
  OutlineArtifact,
  Project,
  ProjectConfig,
  ProjectListResponse,
  RequirementBrief,
  ResearchPack,
  SearchArtifact,
  SlidePlanArtifact,
  SlidePlanPage,
  SlidePlanPageUpdateRequest,
  SvgSlideArtifact,
} from "../types";
```

- [ ] **Step 3: 确认 TypeScript 编译无报错**

```bash
cd ppt-agent-desktop && /Users/zzp/sdk/node/node-v24.13.0-darwin-arm64/bin/npx tsc --noEmit
```

Expected: 无报错

---

## Task 6: 初稿编辑 — 前端 DraftWorkspace（可编辑）

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/App.tsx`

- [ ] **Step 1: 更新 `WorkspaceState` 加入编辑状态**

在 `WorkspaceState` 类型定义末尾（`error: string | null;` 之前）添加：

```typescript
  draftEditState: {
    title: string;
    core_message: string;
    visual_focus: string;
    blocks: Array<{ block_id: string; title: string; content: string; emphasis: string }>;
  } | null;
  isSaving: boolean;
```

同时在 `useState` 初始值中添加：

```typescript
    draftEditState: null,
    isSaving: false,
```

- [ ] **Step 2: 添加 `initDraftEdit` 和 `handleSaveDraftPage` 函数**

在 `handleDrop` 函数之前插入：

```typescript
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
```

- [ ] **Step 3: 替换 `DraftWorkspace` 组件**

将现有 `DraftWorkspace` 函数替换为：

```typescript
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
  editState: WorkspaceState["draftEditState"];
  isSaving: boolean;
  onInitEdit: (page: SlidePlanPage) => void;
  onEditChange: (patch: Partial<WorkspaceState["draftEditState"] & object>) => void;
  onSave: () => void;
}) {
  if (!page) {
    return <EmptyWorkspace title="初稿" description="等待后端生成 slide_plan。" />;
  }

  const isEditing = editState !== null;
  const display = editState ?? {
    title: page.title,
    core_message: page.core_message,
    visual_focus: page.visual_focus,
    blocks: page.blocks,
  };

  return (
    <>
      <div className="workspace-section-heading">
        <span>初稿内容</span>
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

      <div className="workspace-card workspace-card-primary">
        <div className="workspace-meta-row">
          <strong>页面标题</strong>
        </div>
        {isEditing ? (
          <input
            className="draft-edit-input"
            value={display.title}
            onChange={(e) => onEditChange({ title: e.target.value })}
          />
        ) : (
          <h3>{display.title}</h3>
        )}
      </div>

      <div className="workspace-card">
        <div className="workspace-meta-row">
          <strong>核心表达</strong>
          <span className="topic-pill">{page.narrative_role}</span>
        </div>
        {isEditing ? (
          <textarea
            className="draft-edit-textarea"
            value={display.core_message}
            rows={3}
            onChange={(e) => onEditChange({ core_message: e.target.value })}
          />
        ) : (
          <p>{display.core_message}</p>
        )}
      </div>

      <div className="workspace-card-list">
        {display.blocks.map((block, index) => (
          <article className="workspace-card" key={block.block_id}>
            <div className="workspace-meta-row">
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
                <strong>{block.title}</strong>
              )}
              <span className="topic-pill">{`${block.kind} / ${block.emphasis}`}</span>
            </div>
            {isEditing ? (
              <textarea
                className="draft-edit-textarea"
                value={block.content}
                rows={3}
                onChange={(e) => {
                  const next = display.blocks.map((b, i) =>
                    i === index ? { ...b, content: e.target.value } : b
                  );
                  onEditChange({ blocks: next });
                }}
              />
            ) : (
              <p>{block.content}</p>
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
          </article>
        ))}
      </div>

      {brief && !isEditing ? (
        <div className="workspace-card">
          <div className="workspace-meta-row">
            <strong>版式意图</strong>
            <span className="topic-pill">{page.suggested_layout}</span>
          </div>
          <ul className="fact-list">
            <li>{`视觉重心：${page.visual_focus}`}</li>
            <li>{`语气：${brief.tone}`}</li>
            {page.design_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </>
  );
}
```

- [ ] **Step 4: 更新编辑器内 DraftWorkspace 调用处**

找到 `stage === "draft"` 对应的渲染，替换为：

```typescript
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
```

- [ ] **Step 5: 确认 TypeScript 编译无报错**

```bash
cd ppt-agent-desktop && /Users/zzp/sdk/node/node-v24.13.0-darwin-arm64/bin/npx tsc --noEmit
```

Expected: 无报错

- [ ] **Step 6: 提交**

```bash
git add ppt-agent-desktop/src/renderer/types.ts \
        ppt-agent-desktop/src/renderer/services/api.ts \
        ppt-agent-desktop/src/renderer/App.tsx
git commit -m "feat(frontend): add draft page editing with block reorder"
```

---

## Task 7: 初稿编辑 — 前端 DraftPreview（全套 deck 列表）

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/App.tsx`

- [ ] **Step 1: 替换 `DraftPreview` 组件**

将现有 `DraftPreview` 函数替换为：

```typescript
function DraftPreview({
  pages,
  selectedSlideId,
  onSelectSlide,
}: {
  pages: SlidePlanPage[];
  selectedSlideId: string | null;
  onSelectSlide: (slideId: string) => void;
}) {
  if (pages.length === 0) {
    return <EmptyPreview description="初稿阶段会在这里展示全套 PPT 预览。" />;
  }

  return (
    <div className="deck-list-preview">
      {pages.map((page) => (
        <button
          key={page.slide_id}
          className={`deck-list-item ${page.slide_id === selectedSlideId ? "deck-list-item-active" : ""}`}
          onClick={() => onSelectSlide(page.slide_id)}
          type="button"
        >
          <div className="artboard artboard-mini">
            <div className="artboard-title">
              <span className="title-marker" />
              <div className="title-copy">
                <h2>{page.title}</h2>
              </div>
              <div className="title-meta">{`Page ${page.order_no.toString().padStart(2, "0")}`}</div>
            </div>
            <div className="artboard-grid">
              {page.blocks.slice(0, 2).map((block) => (
                <section className="art-card" key={block.block_id}>
                  <div className="art-card-head">
                    <h3>{block.title}</h3>
                  </div>
                  <p className="canvas-copy">{block.content}</p>
                </section>
              ))}
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: 更新编辑器内 DraftPreview 调用处**

找到 `stage === "draft"` 对应的右侧预览区渲染，替换为：

```typescript
              {stage === "draft" ? (
                <DraftPreview
                  pages={workspace.slidePlan?.pages ?? []}
                  selectedSlideId={selectedSlideId}
                  onSelectSlide={(slideId) =>
                    startTransition(() =>
                      setWorkspace((current) => ({ ...current, selectedSlideId: slideId }))
                    )
                  }
                />
              ) : null}
```

- [ ] **Step 3: 确认 TypeScript 编译无报错**

```bash
cd ppt-agent-desktop && /Users/zzp/sdk/node/node-v24.13.0-darwin-arm64/bin/npx tsc --noEmit
```

Expected: 无报错

- [ ] **Step 4: 提交**

```bash
git add ppt-agent-desktop/src/renderer/App.tsx
git commit -m "feat(frontend): replace DraftPreview with full deck scrollable list"
```

---

## Task 8: 设计稿单页重跑 — 后端

**Files:**
- Modify: `ppt-agent/src/ppt_agent/services/project_service.py`
- Modify: `ppt-agent/src/ppt_agent/api/routes/projects.py`
- Create: `ppt-agent/tests/test_svg_rerun.py`

- [ ] **Step 1: 写失败测试**

创建 `ppt-agent/tests/test_svg_rerun.py`：

```python
import pytest
from ppt_agent.schemas.project import ProjectCreateRequest, ProjectConfigPayload
from ppt_agent.schemas.slide_plan import SlidePlanArtifact, SlidePlanPage, SlidePlanBlock
from ppt_agent.schemas.svg import SvgSlideArtifact, SvgSlidePage
from ppt_agent.services.storage_repository import StorageRepository
from ppt_agent.services.project_service import ProjectService


def make_project(service):
    project = service.create_project(ProjectCreateRequest(
        title="SVG 重跑测试",
        topic="测试内容",
        config=ProjectConfigPayload(scenario="汇报", audience="团队", style_pref="简洁"),
    ))
    return project.id


def seed_slide_plan(repository, project_id):
    artifact = SlidePlanArtifact(
        project_id=project_id,
        version=1,
        pages=[
            SlidePlanPage(
                slide_id=f"{project_id}_s1",
                order_no=1,
                title="封面",
                narrative_role="开场",
                core_message="核心消息",
                visual_focus="标题区",
                suggested_layout="cover",
                design_notes=[],
                blocks=[SlidePlanBlock(block_id="b1", kind="text", title="标题", content="内容", words_budget=50, emphasis="high")],
            ),
            SlidePlanPage(
                slide_id=f"{project_id}_s2",
                order_no=2,
                title="背景",
                narrative_role="说明背景",
                core_message="背景消息",
                visual_focus="背景区",
                suggested_layout="content",
                design_notes=[],
                blocks=[SlidePlanBlock(block_id="b2", kind="text", title="背景块", content="背景内容", words_budget=50, emphasis="medium")],
            ),
        ],
    )
    repository.save_artifact(project_id, "slide_plan", artifact.model_dump(mode="json"))


def seed_svg(repository, project_id):
    artifact = SvgSlideArtifact(
        project_id=project_id,
        version=1,
        pages=[
            SvgSlidePage(slide_id=f"{project_id}_s1", order_no=1, title="封面", svg="<svg>原始SVG1</svg>"),
            SvgSlidePage(slide_id=f"{project_id}_s2", order_no=2, title="背景", svg="<svg>原始SVG2</svg>"),
        ],
    )
    repository.save_artifact(project_id, "svg_slide", artifact.model_dump(mode="json"))


def test_regenerate_svg_page_only_updates_target(service, repository):
    project_id = make_project(service)
    seed_slide_plan(repository, project_id)
    seed_svg(repository, project_id)

    result = service.regenerate_svg_page(project_id, f"{project_id}_s1")

    assert result.slide_id == f"{project_id}_s1"
    # 其他页不受影响
    reloaded = service.get_svg(project_id)
    assert reloaded.pages[1].slide_id == f"{project_id}_s2"
    assert len(reloaded.pages) == 2


def test_regenerate_svg_page_persists(service, repository):
    project_id = make_project(service)
    seed_slide_plan(repository, project_id)
    seed_svg(repository, project_id)

    service.regenerate_svg_page(project_id, f"{project_id}_s1")

    reloaded = service.get_svg(project_id)
    assert reloaded.pages[0].slide_id == f"{project_id}_s1"
```

- [ ] **Step 2: 运行确认失败**

```bash
cd ppt-agent && uv run pytest tests/test_svg_rerun.py -v
```

Expected: `AttributeError: 'ProjectService' object has no attribute 'regenerate_svg_page'`

- [ ] **Step 3: 在 `project_service.py` 中实现 `regenerate_svg_page`**

在 `get_svg` 方法后添加：

```python
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
```

在 `_generate_svg_with_fallback` 之前添加私有方法：

```python
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
    prompt = f"""
请根据以下单页策划生成整页 SVG。

项目标题：{project.title}
受众：{project.config.audience}
场景：{project.config.scenario}
风格：{project.config.style_pref}

页面策划：
- 第{plan_page.order_no}页 | {plan_page.title} | {plan_page.core_message} | 布局={plan_page.suggested_layout}
- 块数：{len(plan_page.blocks)}

输出 JSON，格式如下：
{{
  "title": "string",
  "svg": "<svg ...>...</svg>"
}}

要求：
1. svg 必须是完整合法的 SVG 字符串。
2. 画布统一使用 viewBox="0 0 1280 720"。
3. 风格偏向简洁、结构化、适合企业汇报。
""".strip()
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd ppt-agent && uv run pytest tests/test_svg_rerun.py -v
```

Expected: 2 个测试全部 PASS

- [ ] **Step 5: 在 `projects.py` 添加路由**

在文件末尾追加：

```python
@router.post(
    "/{project_id}/svg/pages/{slide_id}/generate",
    response_model=SvgSlidePage,
)
def regenerate_svg_page(project_id: str, slide_id: str) -> SvgSlidePage:
    service = get_project_service()
    try:
        return service.regenerate_svg_page(project_id, slide_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
```

同时更新顶部 import，加入 `SvgSlidePage`：

```python
from ppt_agent.schemas.svg import SvgSlideArtifact, SvgSlidePage
```

- [ ] **Step 6: 提交**

```bash
git add ppt-agent/src/ppt_agent/services/project_service.py \
        ppt-agent/src/ppt_agent/api/routes/projects.py \
        ppt-agent/tests/test_svg_rerun.py
git commit -m "feat(backend): add single-page SVG regeneration"
```

---

## Task 9: 设计稿单页重跑 — 前端

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/types.ts`
- Modify: `ppt-agent-desktop/src/renderer/services/api.ts`
- Modify: `ppt-agent-desktop/src/renderer/App.tsx`

- [ ] **Step 1: `api.ts` 添加 `regenerateSvgPage`**

在 `generateSvg` 后添加：

```typescript
regenerateSvgPage: (projectId: string, slideId: string) =>
  request<SvgSlidePage>(`/api/projects/${projectId}/svg/pages/${slideId}/generate`, {
    method: "POST",
  }),
```

同时更新顶部 import，加入 `SvgSlidePage`：

```typescript
import type {
  // ...现有类型...
  SvgSlidePage,
  SvgSlideArtifact,
} from "../types";
```

- [ ] **Step 2: `WorkspaceState` 添加 `regeneratingSlideId`**

在 `isSaving: boolean;` 之后添加：

```typescript
  regeneratingSlideId: string | null;
```

同时在 `useState` 初始值中添加：

```typescript
    regeneratingSlideId: null,
```

- [ ] **Step 3: 添加 `handleRegenerateSvgPage` 函数**

在 `handleSaveDraftPage` 函数之后添加：

```typescript
  async function handleRegenerateSvgPage(slideId: string) {
    if (!workspace.selectedProjectId) return;
    setWorkspace((current) => ({ ...current, regeneratingSlideId: slideId, error: null }));
    try {
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
    } catch (error) {
      const message = error instanceof Error ? error.message : "重新生成失败";
      startTransition(() => {
        setWorkspace((current) => ({ ...current, regeneratingSlideId: null, error: message }));
      });
    }
  }
```

- [ ] **Step 4: 更新 `DesignWorkspace` 组件，加入重新生成按钮**

将现有 `DesignWorkspace` 函数替换为：

```typescript
function DesignWorkspace({
  page,
  planPage,
  isRegenerating,
  onRegenerate,
}: {
  page: SvgSlidePage | null;
  planPage: SlidePlanPage | null;
  isRegenerating: boolean;
  onRegenerate: () => void;
}) {
  if (!page) {
    return <EmptyWorkspace title="设计稿" description="等待后端生成 svg 设计稿。" />;
  }

  return (
    <>
      <div className="workspace-section-heading">
        <span>设计稿</span>
        <strong>{page.title}</strong>
        <button
          className="ghost-button"
          disabled={isRegenerating}
          onClick={onRegenerate}
          type="button"
        >
          {isRegenerating ? "生成中..." : "重新生成"}
        </button>
      </div>

      <div className="workspace-card workspace-card-primary">
        <div className="workspace-meta-row">
          <strong>渲染结果</strong>
          <span className="topic-pill">{`SVG ${page.svg.length} chars`}</span>
        </div>
        <p>右侧直接展示后端返回的完整 SVG 设计稿。</p>
      </div>

      {planPage ? (
        <div className="workspace-card">
          <div className="workspace-meta-row">
            <strong>设计输入</strong>
            <span className="topic-pill">{planPage.suggested_layout}</span>
          </div>
          <ul className="fact-list">
            <li>{`叙事角色：${planPage.narrative_role}`}</li>
            <li>{`视觉重心：${planPage.visual_focus}`}</li>
            <li>{`区块数量：${planPage.blocks.length}`}</li>
          </ul>
        </div>
      ) : null}
    </>
  );
}
```

- [ ] **Step 5: 更新 DesignWorkspace 调用处**

找到 `stage === "design"` 对应的 `<DesignWorkspace` 渲染（在 `workspace-panel-content` 中），替换为：

```typescript
              {stage === "design" ? (
                <DesignWorkspace
                  page={selectedSvgPage}
                  planPage={selectedPlanPage}
                  isRegenerating={workspace.regeneratingSlideId === selectedSlideId}
                  onRegenerate={() =>
                    selectedSlideId
                      ? void handleRegenerateSvgPage(selectedSlideId)
                      : undefined
                  }
                />
              ) : null}
```

- [ ] **Step 6: 同时更新 StageThumbnail，设计稿缩略图加载态**

在 `StageThumbnail` 组件中，找到 `stage === "design"` 的块，替换为：

```typescript
      {stage === "design" ? (
        svgPage ? (
          <div
            className={`slide-thumb-design-live ${regeneratingSlideId === svgPage.slide_id ? "slide-thumb-loading-overlay" : ""}`}
            dangerouslySetInnerHTML={{ __html: svgPage.svg }}
          />
        ) : (
          <ThumbnailLoading />
        )
      ) : null}
```

同时更新 `StageThumbnail` props 类型，加入 `regeneratingSlideId: string | null`，并在调用处传入 `workspace.regeneratingSlideId`。

- [ ] **Step 7: 确认 TypeScript 编译无报错**

```bash
cd ppt-agent-desktop && /Users/zzp/sdk/node/node-v24.13.0-darwin-arm64/bin/npx tsc --noEmit
```

Expected: 无报错

- [ ] **Step 8: 提交**

```bash
git add ppt-agent-desktop/src/renderer/services/api.ts \
        ppt-agent-desktop/src/renderer/App.tsx
git commit -m "feat(frontend): add single-page SVG regeneration"
```

---

## Task 10: 导出 — 后端依赖 + 服务

**Files:**
- Modify: `ppt-agent/pyproject.toml`
- Modify: `ppt-agent/src/ppt_agent/services/project_service.py`
- Create: `ppt-agent/tests/test_export.py`

- [ ] **Step 1: 安装导出依赖**

```bash
cd ppt-agent && uv add cairosvg pypdf
```

> 注：cairosvg 需要系统 cairo 库。macOS 上执行：`brew install cairo`
> Expected: `uv.lock` 更新

- [ ] **Step 2: 写失败测试**

创建 `ppt-agent/tests/test_export.py`：

```python
import zipfile
import io
import pytest
from ppt_agent.schemas.project import ProjectCreateRequest, ProjectConfigPayload
from ppt_agent.schemas.svg import SvgSlideArtifact, SvgSlidePage
from ppt_agent.services.storage_repository import StorageRepository
from ppt_agent.services.project_service import ProjectService

MINIMAL_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><rect width="1280" height="720" fill="#fff"/><text x="100" y="100">Test</text></svg>'


def make_project_with_svg(service, repository):
    project = service.create_project(ProjectCreateRequest(
        title="导出测试",
        topic="内容",
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
```

- [ ] **Step 3: 运行确认失败**

```bash
cd ppt-agent && uv run pytest tests/test_export.py -v
```

Expected: `AttributeError: 'ProjectService' object has no attribute 'export_svg_zip'`

- [ ] **Step 4: 在 `project_service.py` 实现导出方法**

在 `regenerate_svg_page` 后添加：

```python
def export_svg_zip(self, project_id: str) -> bytes:
    svg_artifact = self.get_svg(project_id)
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for page in sorted(svg_artifact.pages, key=lambda p: p.order_no):
            filename = f"slide_{page.order_no:02d}.svg"
            zf.writestr(filename, page.svg.encode("utf-8"))
    return buffer.getvalue()

def export_pdf(self, project_id: str) -> bytes:
    import cairosvg
    from pypdf import PdfWriter, PdfReader

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
```

（`BytesIO` 已在文件顶部导入，`zipfile` 也已导入）

- [ ] **Step 5: 运行测试确认通过**

```bash
cd ppt-agent && uv run pytest tests/test_export.py -v
```

Expected: 3 个测试全部 PASS

- [ ] **Step 6: 提交**

```bash
git add ppt-agent/pyproject.toml ppt-agent/uv.lock \
        ppt-agent/src/ppt_agent/services/project_service.py \
        ppt-agent/tests/test_export.py
git commit -m "feat(backend): add SVG zip and PDF export services"
```

---

## Task 11: 导出 — 后端路由

**Files:**
- Modify: `ppt-agent/src/ppt_agent/api/routes/projects.py`

- [ ] **Step 1: 添加导出路由**

在文件顶部 import 中加入：

```python
from fastapi.responses import Response
```

在文件末尾追加两个路由：

```python
@router.get("/{project_id}/export/svg")
def export_svg(project_id: str) -> Response:
    service = get_project_service()
    try:
        zip_bytes = service.export_svg_zip(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={project_id}_slides.zip"},
    )


@router.get("/{project_id}/export/pdf")
def export_pdf(project_id: str) -> Response:
    service = get_project_service()
    try:
        pdf_bytes = service.export_pdf(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={project_id}_slides.pdf"},
    )
```

- [ ] **Step 2: 提交**

```bash
git add ppt-agent/src/ppt_agent/api/routes/projects.py
git commit -m "feat(backend): add SVG and PDF export routes"
```

---

## Task 12: 导出 — 前端

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/services/api.ts`
- Modify: `ppt-agent-desktop/src/renderer/App.tsx`

- [ ] **Step 1: `api.ts` 添加导出方法**

在文件末尾（`reorderOutline` 之后）添加：

```typescript
exportSvg: async (projectId: string): Promise<void> => {
  const response = await fetch(`${apiBaseUrl}/api/projects/${projectId}/export/svg`);
  if (!response.ok) throw new Error(`Export failed: ${response.status}`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${projectId}_slides.zip`;
  a.click();
  URL.revokeObjectURL(url);
},
exportPdf: async (projectId: string): Promise<void> => {
  const response = await fetch(`${apiBaseUrl}/api/projects/${projectId}/export/pdf`);
  if (!response.ok) throw new Error(`Export failed: ${response.status}`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${projectId}_slides.pdf`;
  a.click();
  URL.revokeObjectURL(url);
},
```

- [ ] **Step 2: 在 `App.tsx` 中，将顶部导出按钮改为下拉菜单**

在 `App` 组件的 state 中添加：

```typescript
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
```

找到顶部工具栏中的：

```tsx
          <button className="export-button" type="button">
            导出
          </button>
```

替换为：

```tsx
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
```

- [ ] **Step 3: 确认 TypeScript 编译无报错**

```bash
cd ppt-agent-desktop && /Users/zzp/sdk/node/node-v24.13.0-darwin-arm64/bin/npx tsc --noEmit
```

Expected: 无报错

- [ ] **Step 4: 提交**

```bash
git add ppt-agent-desktop/src/renderer/services/api.ts \
        ppt-agent-desktop/src/renderer/App.tsx
git commit -m "feat(frontend): add SVG and PDF export dropdown"
```

---

## Task 13: Tavily 联网搜索 — 后端

**Files:**
- Modify: `ppt-agent/pyproject.toml`
- Modify: `ppt-agent/src/ppt_agent/config.py`
- Modify: `ppt-agent/src/ppt_agent/services/project_service.py`
- Modify: `ppt-agent/src/ppt_agent/api/routes/health.py`
- Create: `ppt-agent/tests/test_tavily.py`

- [ ] **Step 1: 安装 tavily-python**

```bash
cd ppt-agent && uv add tavily-python
```

Expected: `uv.lock` 更新

- [ ] **Step 2: 在 `config.py` 添加 Tavily 配置**

在 `gemini_model` 字段之后添加：

```python
    tavily_api_key: str | None = None
```

- [ ] **Step 3: 写 Tavily 集成测试（离线 mock）**

创建 `ppt-agent/tests/test_tavily.py`：

```python
import pytest
from unittest.mock import patch, MagicMock
from ppt_agent.schemas.project import ProjectCreateRequest, ProjectConfigPayload, ProjectResponse
from ppt_agent.schemas.project import ProjectConfigPayload
from ppt_agent.services.project_service import ProjectService
from datetime import UTC, datetime


def make_project_response(project_id: str = "proj_test") -> ProjectResponse:
    return ProjectResponse(
        id=project_id,
        title="测试项目",
        topic="AI 运维平台介绍，重点突出监控和告警能力",
        status="draft",
        config=ProjectConfigPayload(
            scenario="汇报", audience="团队", style_pref="科技",
            research_enabled=True,
        ),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_fetch_search_results_returns_list(service: ProjectService):
    project = make_project_response()
    mock_result = {
        "results": [
            {"title": "AI 运维最佳实践", "url": "https://example.com/1", "content": "内容摘要1"},
            {"title": "监控系统选型", "url": "https://example.com/2", "content": "内容摘要2"},
        ]
    }
    with patch("ppt_agent.services.project_service.TavilyClient") as MockClient:
        instance = MockClient.return_value
        instance.search.return_value = mock_result
        results = service._fetch_tavily_results(project, api_key="fake-key")

    assert len(results) == 2
    assert results[0]["title"] == "AI 运维最佳实践"


def test_fetch_search_results_skips_when_no_key(service: ProjectService):
    project = make_project_response()
    results = service._fetch_tavily_results(project, api_key=None)
    assert results == []


def test_build_research_prompt_includes_search_results(service: ProjectService):
    project = make_project_response()
    search_results = [
        {"title": "标题1", "url": "https://a.com", "content": "摘要1"},
    ]
    prompt = service._build_research_prompt(project, search_results=search_results)
    assert "标题1" in prompt
    assert "https://a.com" in prompt
```

- [ ] **Step 4: 运行确认失败**

```bash
cd ppt-agent && uv run pytest tests/test_tavily.py -v
```

Expected: `AttributeError: ... _fetch_tavily_results`

- [ ] **Step 5: 在 `project_service.py` 实现 Tavily 相关方法**

在文件顶部已有导入后加入：

```python
try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None  # type: ignore[assignment,misc]
```

在 `_generate_research_with_fallback` 上方添加：

```python
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
```

- [ ] **Step 6: 更新 `_generate_research_with_fallback` 使用 Tavily**

将现有方法替换为：

```python
def _generate_research_with_fallback(self, project: ProjectResponse) -> ResearchPack:
    settings = get_settings()
    search_results = self._fetch_tavily_results(project, api_key=settings.tavily_api_key)
    try:
        return self._generate_research_with_model(project, search_results=search_results)
    except (ModelProviderError, ValidationError, ValueError, json.JSONDecodeError):
        return self._generate_research_fallback(project)
```

- [ ] **Step 7: 更新 `_generate_research_with_model` 接受 search_results 参数**

将方法签名改为：

```python
def _generate_research_with_model(
    self,
    project: ProjectResponse,
    search_results: list[dict[str, str]] | None = None,
) -> ResearchPack:
```

并更新 `_build_research_prompt` 调用：

```python
        prompt=self._build_research_prompt(project, search_results=search_results or []),
```

- [ ] **Step 8: 更新 `_build_research_prompt` 注入搜索结果**

找到 `_build_research_prompt` 方法，将其签名改为：

```python
def _build_research_prompt(
    self,
    project: ProjectResponse,
    search_results: list[dict[str, str]] | None = None,
) -> str:
```

在现有 prompt 末尾（return 语句之前）加入搜索结果注入：

```python
    search_section = ""
    if search_results:
        lines = "\n".join(
            f"- [{item['title']}]({item['url']}): {item['content'][:200]}"
            for item in search_results
        )
        search_section = f"\n\n以下是来自外部搜索的参考资料（请优先引用）：\n{lines}"
```

并在 `return` 的字符串末尾拼接 `search_section`。

- [ ] **Step 9: 运行测试确认通过**

```bash
cd ppt-agent && uv run pytest tests/test_tavily.py -v
```

Expected: 3 个测试全部 PASS

- [ ] **Step 10: 更新 `/api/health` 路由，加入 Tavily 状态**

在 `health.py` 的 `get_health` 函数中，`services` 字典加入：

```python
            "tavily": (
                ServiceStatus(status="ok", detail="Tavily API key is configured.")
                if settings.tavily_api_key
                else ServiceStatus(status="not_configured", detail="Set PPT_AGENT_TAVILY_API_KEY to enable web search.")
            ),
```

- [ ] **Step 11: 提交**

```bash
git add ppt-agent/pyproject.toml ppt-agent/uv.lock \
        ppt-agent/src/ppt_agent/config.py \
        ppt-agent/src/ppt_agent/services/project_service.py \
        ppt-agent/src/ppt_agent/api/routes/health.py \
        ppt-agent/tests/test_tavily.py
git commit -m "feat(backend): integrate Tavily web search into research generation"
```

---

## Task 14: Review Engine — 后端

**Files:**
- Create: `ppt-agent/src/ppt_agent/schemas/review.py`
- Modify: `ppt-agent/src/ppt_agent/services/project_service.py`
- Modify: `ppt-agent/src/ppt_agent/api/routes/projects.py`
- Create: `ppt-agent/tests/test_review.py`

- [ ] **Step 1: 创建 `review.py` schema**

创建 `ppt-agent/src/ppt_agent/schemas/review.py`：

```python
from typing import Literal
from pydantic import BaseModel


class ReviewIssue(BaseModel):
    code: str
    severity: Literal["error", "warning", "info"]
    detail: str


class ReviewPage(BaseModel):
    slide_id: str
    order_no: int
    issues: list[ReviewIssue]
    passed: bool


class ReviewArtifact(BaseModel):
    project_id: str
    version: int
    pages: list[ReviewPage]
```

- [ ] **Step 2: 写失败测试**

创建 `ppt-agent/tests/test_review.py`：

```python
import pytest
from ppt_agent.schemas.project import ProjectCreateRequest, ProjectConfigPayload
from ppt_agent.schemas.svg import SvgSlideArtifact, SvgSlidePage
from ppt_agent.services.storage_repository import StorageRepository
from ppt_agent.services.project_service import ProjectService

VALID_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><rect width="1280" height="720" fill="#fff"/><text x="100" y="100">Hello World, 这是一段测试文字</text></svg>'
NO_VIEWBOX_SVG = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="1280" height="720" fill="#fff"/><text x="100" y="100">内容</text></svg>'
BROKEN_SVG = "<svg><broken"
EMPTY_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><rect width="1280" height="720" fill="#fff"/></svg>'


def setup_project_with_svg(service, repository, svgs: list[str]):
    project = service.create_project(ProjectCreateRequest(
        title="Review 测试",
        topic="内容",
        config=ProjectConfigPayload(scenario="汇报", audience="团队", style_pref="简洁"),
    ))
    artifact = SvgSlideArtifact(
        project_id=project.id,
        version=1,
        pages=[
            SvgSlidePage(slide_id=f"{project.id}_s{i+1}", order_no=i+1, title=f"页{i+1}", svg=svg)
            for i, svg in enumerate(svgs)
        ],
    )
    repository.save_artifact(project.id, "svg_slide", artifact.model_dump(mode="json"))
    return project.id


def test_review_valid_svg_passes(service, repository):
    project_id = setup_project_with_svg(service, repository, [VALID_SVG])
    result = service.run_review(project_id)

    assert len(result.pages) == 1
    assert result.pages[0].passed is True
    assert result.pages[0].issues == []


def test_review_detects_no_viewbox(service, repository):
    project_id = setup_project_with_svg(service, repository, [NO_VIEWBOX_SVG])
    result = service.run_review(project_id)

    codes = [issue.code for issue in result.pages[0].issues]
    assert "missing_viewbox" in codes


def test_review_detects_broken_svg(service, repository):
    project_id = setup_project_with_svg(service, repository, [BROKEN_SVG])
    result = service.run_review(project_id)

    codes = [issue.code for issue in result.pages[0].issues]
    assert "invalid_xml" in codes
    assert result.pages[0].passed is False


def test_review_detects_no_text(service, repository):
    project_id = setup_project_with_svg(service, repository, [EMPTY_SVG])
    result = service.run_review(project_id)

    codes = [issue.code for issue in result.pages[0].issues]
    assert "no_text_content" in codes


def test_review_persists(service, repository):
    project_id = setup_project_with_svg(service, repository, [VALID_SVG])
    service.run_review(project_id)

    reloaded = service.get_review(project_id)
    assert reloaded.project_id == project_id
    assert len(reloaded.pages) == 1
```

- [ ] **Step 3: 运行确认失败**

```bash
cd ppt-agent && uv run pytest tests/test_review.py -v
```

Expected: `AttributeError: 'ProjectService' object has no attribute 'run_review'`

- [ ] **Step 4: 在 `project_service.py` 实现 review 方法**

在顶部 import 中加入：

```python
from xml.etree import ElementTree
from ppt_agent.schemas.review import ReviewArtifact, ReviewIssue, ReviewPage
```

在 `export_pdf` 方法后添加：

```python
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
    ns = {"svg": "http://www.w3.org/2000/svg"}
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
```

- [ ] **Step 5: 运行测试确认通过**

```bash
cd ppt-agent && uv run pytest tests/test_review.py -v
```

Expected: 5 个测试全部 PASS

- [ ] **Step 6: 在 `projects.py` 添加 review 路由**

在顶部 import 中加入：

```python
from ppt_agent.schemas.review import ReviewArtifact
```

在文件末尾追加：

```python
@router.post("/{project_id}/review/run", response_model=ReviewArtifact)
def run_review(project_id: str) -> ReviewArtifact:
    service = get_project_service()
    try:
        return service.run_review(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{project_id}/review", response_model=ReviewArtifact)
def get_review(project_id: str) -> ReviewArtifact:
    service = get_project_service()
    try:
        return service.get_review(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
```

- [ ] **Step 7: 运行全部测试确认无回归**

```bash
cd ppt-agent && uv run pytest tests/ -v
```

Expected: 全部 PASS

- [ ] **Step 8: 提交**

```bash
git add ppt-agent/src/ppt_agent/schemas/review.py \
        ppt-agent/src/ppt_agent/services/project_service.py \
        ppt-agent/src/ppt_agent/api/routes/projects.py \
        ppt-agent/tests/test_review.py
git commit -m "feat(backend): add SVG review engine"
```

---

## Task 15: Review Engine — 前端

**Files:**
- Modify: `ppt-agent-desktop/src/renderer/types.ts`
- Modify: `ppt-agent-desktop/src/renderer/services/api.ts`
- Modify: `ppt-agent-desktop/src/renderer/App.tsx`

- [ ] **Step 1: `types.ts` 添加 review 类型**

在文件末尾追加：

```typescript
export type ReviewIssue = {
  code: string;
  severity: "error" | "warning" | "info";
  detail: string;
};

export type ReviewPage = {
  slide_id: string;
  order_no: number;
  issues: ReviewIssue[];
  passed: boolean;
};

export type ReviewArtifact = {
  project_id: string;
  version: number;
  pages: ReviewPage[];
};
```

- [ ] **Step 2: `api.ts` 添加 review 方法**

更新顶部 import 加入 `ReviewArtifact`，然后在 `exportPdf` 之后添加：

```typescript
runReview: (projectId: string) =>
  request<ReviewArtifact>(`/api/projects/${projectId}/review/run`, {
    method: "POST",
  }),
getReview: (projectId: string) =>
  request<ReviewArtifact>(`/api/projects/${projectId}/review`),
```

- [ ] **Step 3: `WorkspaceState` 添加 review 状态**

在 `regeneratingSlideId` 之后添加：

```typescript
  reviewArtifact: ReviewArtifact | null;
  isReviewing: boolean;
```

同时在初始值中添加：

```typescript
    reviewArtifact: null,
    isReviewing: false,
```

- [ ] **Step 4: 添加 `handleRunReview` 函数**

在 `handleRegenerateSvgPage` 之后添加：

```typescript
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
```

- [ ] **Step 5: 更新 `DesignWorkspace` 加入检查按钮和 review 面板**

将 `DesignWorkspace` 的 props 类型加入 review 相关字段：

```typescript
function DesignWorkspace({
  page,
  planPage,
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
```

在"重新生成"按钮旁边加入"检查"按钮（在 `workspace-section-heading` 的末尾）：

```tsx
        <button
          className="ghost-button"
          disabled={isReviewing}
          onClick={onRunReview}
          type="button"
        >
          {isReviewing ? "检查中..." : "检查"}
        </button>
```

在组件末尾（最后一个 `null` 之前）加入 review 面板：

```tsx
      {reviewPage ? (
        <div className={`workspace-card ${reviewPage.passed ? "" : "workspace-card-warning"}`}>
          <div className="workspace-meta-row">
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
            <p>所有检查项均通过。</p>
          )}
        </div>
      ) : null}
```

- [ ] **Step 6: 更新 `DesignWorkspace` 调用处，传入 review 相关 props**

```typescript
              {stage === "design" ? (
                <DesignWorkspace
                  page={selectedSvgPage}
                  planPage={selectedPlanPage}
                  isRegenerating={workspace.regeneratingSlideId === selectedSlideId}
                  onRegenerate={() =>
                    selectedSlideId
                      ? void handleRegenerateSvgPage(selectedSlideId)
                      : undefined
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
```

- [ ] **Step 7: 更新 `StageThumbnail`，设计稿阶段在缩略图上标注 review 问题**

在 `StageThumbnail` props 中加入 `reviewPage?: ReviewPage`，在设计稿缩略图的渲染中，在 `svgPage` 存在时额外显示红点：

```tsx
      {stage === "design" && svgPage ? (
        <div className="slide-thumb-design-wrapper">
          <div
            className={`slide-thumb-design-live ${regeneratingSlideId === svgPage.slide_id ? "slide-thumb-loading-overlay" : ""}`}
            dangerouslySetInnerHTML={{ __html: svgPage.svg }}
          />
          {reviewPage && !reviewPage.passed ? (
            <span className="slide-thumb-issue-dot" title="检查发现问题" />
          ) : null}
        </div>
      ) : stage === "design" ? (
        <ThumbnailLoading />
      ) : null}
```

更新 `StageThumbnail` 调用处传入 `reviewPage`：

```tsx
                  reviewPage={workspace.reviewArtifact?.pages.find(
                    (page) => page.slide_id === slide.slide_id
                  )}
```

- [ ] **Step 8: 确认 TypeScript 编译无报错**

```bash
cd ppt-agent-desktop && /Users/zzp/sdk/node/node-v24.13.0-darwin-arm64/bin/npx tsc --noEmit
```

Expected: 无报错

- [ ] **Step 9: 提交**

```bash
git add ppt-agent-desktop/src/renderer/types.ts \
        ppt-agent-desktop/src/renderer/services/api.ts \
        ppt-agent-desktop/src/renderer/App.tsx
git commit -m "feat(frontend): add review panel and issue indicators"
```

---

## 自检结果

**Spec 覆盖验证：**
- ✅ 初稿块级编辑（Task 2-7）
- ✅ 右侧全套 deck 列表（Task 7）
- ✅ 设计稿单页重跑（Task 8-9）
- ✅ SVG / PDF 导出（Task 10-12）
- ✅ Tavily 联网搜索（Task 13）
- ✅ Review Engine 后端（Task 14）
- ✅ Review Engine 前端（Task 15）

**类型一致性：**
- `SlidePlanPageUpdateRequest` 定义于 Task 2，在 Task 3-5 中引用 ✅
- `SvgSlidePage` 定义于现有代码，在 Task 8-9 中引用 ✅
- `ReviewArtifact` / `ReviewPage` / `ReviewIssue` 定义于 Task 14，在 Task 15 中引用 ✅
- `WorkspaceState` 扩展字段 `draftEditState`、`isSaving`、`regeneratingSlideId`、`reviewArtifact`、`isReviewing` 在 App.tsx 各处使用一致 ✅
