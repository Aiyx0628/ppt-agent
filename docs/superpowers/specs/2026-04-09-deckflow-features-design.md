# DeckFlow 未完成功能设计文档

日期：2026-04-09

## 1. 背景

当前仓库已完成完整的主链路：`intake → research → brief → outline → search → slide_plan → svg`，前后端三栏编辑器已接真实 artifact。

本文档描述接下来需要补全的五个功能模块，按实施优先级排列，采用方案 A（逐功能全栈推进）。

---

## 2. 功能一：初稿编辑能力（完整版）

### 2.1 后端

新增单页更新接口：

```
PATCH /api/projects/{project_id}/slide-plan/pages/{slide_id}
```

请求体（部分更新）：
```json
{
  "title": "...",
  "core_message": "...",
  "visual_focus": "...",
  "blocks": [
    { "block_id": "...", "title": "...", "content": "...", "emphasis": "high" }
  ]
}
```

实现：
- 读出当前 `slide_plan` artifact JSON
- 替换对应 `slide_id` 的页数据
- 写回文件
- 返回更新后的 `SlidePlanPage`

无需新建数据库表，复用现有文件存储层。

### 2.2 前端

**中间内容区（DraftWorkspace）：**
- 页标题 → `<input>` 可编辑
- 每个 block 的 title / content → `<textarea>` 可编辑
- 块之间支持拖拽排序（复用 HTML drag API，与 outline 拖拽一致）
- 底部固定"保存"按钮 → 调用 `PATCH` 接口 → 成功后刷新当前页状态

**右侧预览区（DraftPreview）：**
从"当前页 artboard"改为可滚动的全套 deck 列表：
- 纵向排列所有页的 artboard 缩略版
- 当前选中页高亮边框
- 点击跳转选中页

### 2.3 新增 API / 类型

- `types.ts`：新增 `SlidePlanPageUpdateRequest`
- `api.ts`：新增 `updateSlidePlanPage(projectId, slideId, payload)`

---

## 3. 功能二：设计稿单页重跑

### 3.1 后端

新增单页 SVG 重跑接口：

```
POST /api/projects/{project_id}/svg/pages/{slide_id}/generate
```

实现：
- 读取该页的 `slide_plan` 数据
- 用现有 SVG 生成逻辑重新生成单页 SVG
- 更新 `svg_artifact` JSON 中对应页
- 写回文件
- 返回更新后的 `SvgSlidePage`

### 3.2 前端

**DesignWorkspace：**
- 在当前页信息面板中增加"重新生成"按钮
- 点击后：该页缩略图显示加载态，主预览区显示骨架屏
- 生成完成后只刷新 `svgArtifact` 中该页数据，其他页不受影响

**左侧缩略图：**
- 设计稿阶段缩略图正在生成时显示 loading 状态
- 生成完立即更新

### 3.3 新增 API / 类型

- `api.ts`：新增 `regenerateSvgPage(projectId, slideId)`
- 返回类型复用现有 `SvgSlidePage`

---

## 4. 功能三：导出（SVG / PDF）

### 4.1 后端

新增两个导出接口：

```
GET /api/projects/{project_id}/export/svg
GET /api/projects/{project_id}/export/pdf
```

**SVG 导出：**
- 读取 `svg_artifact` 中所有页
- 打包为 `.zip`（每页一个 `slide_01.svg` 文件）
- 返回 `application/zip`

**PDF 导出：**
- 读取所有 SVG 页
- 用 `cairosvg` 逐页转 PNG
- 用 `fpdf2` 拼成 PDF
- 返回 `application/pdf`

新增依赖：`cairosvg`、`fpdf2`

### 4.2 前端

顶部工具栏"导出"按钮改为下拉菜单：
- 导出 SVG（zip）
- 导出 PDF

点击后调用对应接口，用 `<a download>` 触发浏览器下载。

### 4.3 新增 API / 类型

- `api.ts`：新增 `exportSvg(projectId)`、`exportPdf(projectId)`，返回 `Blob`

---

## 5. 功能四：联网搜索接入（Tavily）

### 5.1 后端

在 `generate_research` 流程中接入 Tavily Search API。

**配置：**
- `.env` 新增 `PPT_AGENT_TAVILY_API_KEY`
- `config.py` 统一读取

**实现流程：**
1. 基于 `project.topic` 提取 2-3 个搜索关键词（用现有模型调用）
2. 对每个关键词调用 Tavily API，拿到 `title / url / content / score`
3. 将搜索结果注入 `_generate_research_with_fallback` 的 prompt 上下文
4. 模型基于真实搜索结果生成 `ResearchPack`

**降级策略：**
- `PPT_AGENT_TAVILY_API_KEY` 未配置时，静默回退到当前纯模型生成逻辑，不报错

**健康检查：**
- `/api/health` 的 `services` 中新增 `tavily: ok / not_configured`

### 5.2 前端

无新增 UI。联网搜索通过已有 `project.config.research_enabled` 字段控制，本期固定为"有 key 就用"。

---

## 6. 功能五：Review Engine

### 6.1 后端

新增 review 接口：

```
POST /api/projects/{project_id}/review/run
GET  /api/projects/{project_id}/review
```

**首版检查项（规则检查，不调模型）：**
- SVG 宽高是否合法（需含 `viewBox` 或明确 `width/height`）
- 文字节点是否存在（防止空白页）
- 单页文字总长度是否超出阈值（防止文字溢出）
- SVG 是否可被 `ElementTree` 解析（基础结构合法性）

**结果结构：**
```json
{
  "project_id": "...",
  "version": 1,
  "pages": [
    {
      "slide_id": "...",
      "order_no": 1,
      "issues": [
        { "code": "text_overflow", "severity": "warning", "detail": "..." }
      ],
      "passed": false
    }
  ]
}
```

存为 `review` artifact，复用现有存储层。

### 6.2 前端

设计稿阶段工具栏新增"检查"按钮：
- 调用 `run` 接口
- 在右侧或底部显示 review 结果面板
  - 每页显示通过 / 警告 / 失败状态
  - 点击具体问题 → 跳转到该页 + 高亮提示
  - 有问题的页在左侧缩略图上显示小红点

### 6.3 新增 API / 类型

- `types.ts`：新增 `ReviewArtifact`、`ReviewPage`、`ReviewIssue`
- `api.ts`：新增 `runReview(projectId)`、`getReview(projectId)`

---

## 7. 实施顺序

严格按以下顺序逐功能全栈推进：

1. 初稿编辑能力（完整版）
2. 设计稿单页重跑
3. 导出（SVG / PDF）
4. 联网搜索接入
5. Review Engine
