# DeckFlow 产品与工程架构文档（适合交给大模型阅读）

## 0. 文档目标

这是一份面向大模型与工程团队的统一说明文档，用于指导一个 **AI PPT 生产系统** 的产品设计与工程实现。

本项目的目标不是做一个“一键套模板出 PPT”的工具，而是做一个 **把 PPT 生产过程拆解成多个可编辑、可回退、可重跑阶段的桌面产品**。

本项目技术前提如下：

- 前端：**Electron**
- 后端：**Python**
- 数据库：**PostgreSQL**
- 文件存储：**本地文件系统**（不使用云对象存储）
- 大模型：通过统一 Model Router 接入多个模型提供方
- 工作流：建议采用可恢复、可重试的任务编排模式

---

# 1. 产品定义

## 1.1 产品名称

项目代号：**DeckFlow**

## 1.2 产品定位

DeckFlow 是一个桌面端 AI PPT 生产系统。

它帮助用户完成以下工作：

1. 明确汇报目标
2. 补全需求信息
3. 自动调研相关资料
4. 生成逻辑化大纲
5. 对每一页做内容策划
6. 对每一页做视觉设计
7. 输出可预览、可修改、可导出的 PPT 初稿

## 1.3 核心价值

本产品不追求“最快出图”，而追求：

- 内容正确
- 结构清晰
- 页面稳定
- 支持局部修改
- 支持单页重跑
- 支持版本管理

## 1.4 目标用户

第一阶段目标用户：

1. 产品经理
2. 售前/咨询顾问
3. 企业内部汇报人员
4. 需要频繁写方案、总结、路演材料的知识工作者

## 1.5 MVP 范围

MVP 只做以下能力：

1. 创建项目
2. 通过 AI 生成与确认需求 Brief
3. 自动调研资料（可选）
4. 自动生成 PPT 大纲
5. 自动生成逐页策划稿
6. 自动生成逐页设计稿
7. 自动渲染页面预览
8. 自动导出 PDF / PPTX / SVG
9. 支持单页重跑与简单编辑

不做：

- 多人实时协作
- 企业审批流
- 复杂动画
- 在线模板商城
- 云端对象存储

---

# 2. 产品主流程

完整用户流程如下：

```text
新建项目
→ 输入主题/用途/受众/页数/风格
→ AI 提问补全需求
→ 用户确认 Brief
→ AI 调研资料
→ AI 生成大纲
→ 用户修改/拖拽大纲
→ AI 逐页生成策划稿
→ AI 逐页生成设计稿
→ 页面渲染与质量检查
→ 用户局部修改/单页重跑
→ 导出 PDF / PPTX / SVG
```

---

# 3. 业务流程拆解（逐步骤）

## 步骤 1：创建项目

用户输入：

- 项目标题
- 演示主题
- 使用场景（汇报/方案/路演/培训/总结）
- 受众（老板/客户/团队）
- 页数范围
- 风格偏好（商务/科技/简洁）
- 是否联网调研
- 是否需要讲稿

系统产物：

- `project`
- `project_config`

## 步骤 2：需求澄清

Requirement Agent 根据用户输入生成关键澄清问题，例如：

- 这份 PPT 的目标是什么？
- 希望受众在看完之后采取什么行动？
- 是否有必须出现的数据、案例、产品信息？
- 是否有禁用内容或敏感信息？
- 更偏分析型、说服型还是汇报型？

用户回答后，系统生成：

- `requirement_brief`

## 步骤 3：资料调研

如果启用调研：

- Research Agent 基于主题进行检索
- 整理资料摘要
- 抽取关键事实
- 标记来源与可信度
- 为后续大纲生成提供输入

系统产物：

- `research_pack`
- `source_refs`

## 步骤 4：生成大纲

Outline Agent 基于 `requirement_brief + research_pack` 生成：

- 封面
- 目录
- 一级章节
- 每页标题
- 每页核心信息
- 每页页面类型建议

用户可以：

- 拖拽排序
- 删除页面
- 新增页面
- 修改标题
- 修改章节逻辑

系统产物：

- `outline`

## 步骤 5：逐页策划

Planning Agent 为每一页生成策划稿，不直接画页面，而是先回答：

- 这页最重要的结论是什么？
- 哪块内容是视觉重点？
- 适合用什么页面类型？
- 应该使用哪些内容块？
- 各内容块的字数预算是多少？
- 布局意图是什么？

系统产物：

- `slide_plan[]`

## 步骤 6：逐页设计

Design Agent 基于策划稿与主题系统生成：

- 字体层级
- 色彩映射
- 布局结构
- 卡片区块
- 图表/图标占位
- 背景样式
- 设计规格

系统产物：

- `design_spec[]`

## 步骤 7：页面渲染

Renderer 将 `design_spec` 转换为：

- `svg`
- `png` 缩略图
- 页面预览快照

推荐策略：

- **大模型负责生成 Design Spec JSON**
- **Renderer 代码负责将 JSON 转换为 SVG**

不要让模型直接自由输出最终 SVG，避免结构失控。

## 步骤 8：质量检查与自动修复

Review Agent 检查：

- 文本溢出
- 区块重叠
- 字号过小
- 留白不足
- 页面层级不清晰
- 多页风格不一致
- 章节逻辑断裂

输出：

- `review_report`

## 步骤 9：编辑与局部重跑

用户可以执行：

- 修改单页标题
- 修改单页重点
- 切换页面类型
- 切换布局模式
- 单页重跑
- 只重跑策划层
- 只重跑设计层

## 步骤 10：导出

支持导出：

- PDF
- PPTX
- SVG 打包
- 页面图片包

Electron 负责：

- 打开系统保存对话框
- 选择导出路径
- 写入本地文件
- 打开导出目录

---

# 4. 技术架构

## 4.1 总体架构

```text
Electron App
├─ Main Process
│  ├─ App lifecycle
│  ├─ Window management
│  ├─ Local file bridge
│  ├─ Secure IPC
│  └─ Auto update
│
├─ Preload
│  └─ Expose safe APIs to renderer
│
└─ Renderer Process
   ├─ Project Studio
   ├─ Brief Editor
   ├─ Outline Editor
   ├─ Slide Planner UI
   ├─ Preview UI
   └─ Export UI

Python Backend
├─ FastAPI API Service
├─ Workflow Orchestrator
├─ Agent Services
│  ├─ Requirement Agent
│  ├─ Research Agent
│  ├─ Outline Agent
│  ├─ Planning Agent
│  ├─ Design Agent
│  ├─ Review Agent
│  └─ Export Agent
├─ Renderer Service
├─ File Service
├─ Model Router
└─ PostgreSQL
```

## 4.2 架构原则

1. Electron 只负责桌面壳、本地桥接、文件交互、页面展示。
2. Python 后端负责业务逻辑、任务编排、模型调用、渲染、导出。
3. 所有生成过程都必须有结构化中间产物。
4. 每个阶段都必须可重跑、可回退、可版本化。
5. 文件统一存储在本地文件系统。
6. 元数据、索引、状态统一存入 PostgreSQL。

---

# 5. Electron 前端架构

## 5.1 进程模型

### Main Process

负责：

- 应用启动与退出
- 窗口管理
- 自动更新
- 原生菜单
- 系统对话框
- 本地文件读写桥接
- IPC 注册

### Preload

负责：

- 暴露白名单 API 给 Renderer
- 参数校验
- 隔离高权限能力

### Renderer

负责：

- UI 界面
- 页面状态管理
- 可视化编辑器
- 预览与任务状态展示
- 调用后端 API

## 5.2 建议页面

至少包括：

1. 项目首页
2. 项目配置页
3. Brief 页
4. 大纲编辑页
5. 策划页
6. 设计预览页
7. 导出页

---

# 6. Python 后端架构

## 6.1 推荐技术栈

- API：FastAPI
- ORM：SQLAlchemy 2.x
- 数据校验：Pydantic
- 数据库：PostgreSQL
- 缓存：Redis（可选）
- 模型调用：httpx + 自建 Model Router
- 文件处理：pathlib / aiofiles
- 日志：structlog 或 loguru
- 监控：Prometheus / OpenTelemetry / Sentry

## 6.2 工作流架构建议

推荐把生成链路设计成持久化工作流，而不是单个同步接口。

可以采用两种方式：

### 方案 A：简化版

- FastAPI + 内部任务队列 + PostgreSQL 状态表
- 适合 MVP

### 方案 B：标准版

- FastAPI + Workflow Orchestrator（如 Temporal 类模式）
- 适合正式工程化

如果当前目标是快速做 MVP，建议先做方案 A，再升级到可恢复工作流。

---

# 7. 核心后端模块

## 7.1 API Gateway

职责：

- 登录鉴权
- 项目 CRUD
- 启动生成任务
- 查询任务状态
- 查询中间产物
- 导出与下载

## 7.2 Model Router

职责：

- 统一接入不同模型提供方
- 管理模型路由策略
- 管理模型 fallback
- 记录 token、耗时、成本
- 管理 prompt 版本

## 7.3 Artifact Service

职责：

- 保存每个阶段产物
- 管理版本
- 比较差异
- 支持回滚

## 7.4 Agent Services

拆分为：

- Requirement Agent
- Research Agent
- Outline Agent
- Planning Agent
- Design Agent
- Review Agent
- Export Agent

## 7.5 Renderer Service

职责：

- `design_spec -> svg`
- 生成缩略图
- 执行布局安全检查
- 输出预览资源

## 7.6 File Service

职责：

- 管理项目本地目录
- 保存 artifacts
- 保存导出文件
- 保存临时渲染文件
- 删除废弃版本文件

---

# 8. 本地文件存储设计

## 8.1 存储原则

不使用云对象存储，统一使用 **本地文件系统**。

数据库只保存：

- 文件元数据
- 文件路径
- 文件 hash
- 版本号
- 所属项目
- 所属 slide

真正文件保存在磁盘目录。

## 8.2 推荐目录结构

```text
storage/
  projects/
    {project_id}/
      project.json
      exports/
        output.pdf
        output.pptx
      artifacts/
        brief/
          v1.json
          v2.json
        research/
          v1.json
        outline/
          v1.json
          v2.json
        slides/
          {slide_id}/
            plan/
              v1.json
            design/
              v1.json
            render/
              v1.svg
              v1.png
            review/
              v1.json
      temp/
        render-cache/
```

## 8.3 文件命名规则

建议统一命名：

- `v1.json`
- `v2.json`
- `v3.json`

或者：

- `20260409T143000Z_v1.json`

要求：

- 可排序
- 可追溯
- 可回滚

---

# 9. PostgreSQL 数据模型

## 9.1 核心表列表

建议最少有以下表：

1. `users`
2. `projects`
3. `project_configs`
4. `slides`
5. `artifacts`
6. `artifact_versions`
7. `workflow_runs`
8. `slide_jobs`
9. `exports`
10. `model_calls`
11. `review_reports`

## 9.2 表说明

### users

用户信息。

### projects

项目主表。

字段建议：

- id
- owner_id
- title
- status
- theme_id
- page_limit
- created_at
- updated_at

### project_configs

项目配置表。

字段建议：

- project_id
- scenario
- audience
- style_pref
- research_enabled
- narration_enabled

### slides

页面表。

字段建议：

- id
- project_id
- order_no
- title
- slide_type
- status
- created_at
- updated_at

### artifacts

中间产物索引表。

字段建议：

- id
- project_id
- slide_id nullable
- artifact_type
- current_version
- current_file_path
- created_at

### artifact_versions

产物版本表。

字段建议：

- id
- artifact_id
- version_no
- file_path
- file_hash
- model_name
- prompt_version
- created_at

### workflow_runs

项目级工作流运行表。

字段建议：

- id
- project_id
- workflow_type
- status
- started_at
- ended_at
- error_message

### slide_jobs

页面级任务表。

字段建议：

- id
- project_id
- slide_id
- stage
- status
- started_at
- ended_at
- error_message

### exports

导出记录表。

字段建议：

- id
- project_id
- export_type
- file_path
- created_at

### model_calls

模型调用表。

字段建议：

- id
- project_id
- slide_id nullable
- stage
- provider
- model
- prompt_tokens
- completion_tokens
- latency_ms
- cost_estimate
- success
- created_at

### review_reports

质量检查报告表。

字段建议：

- id
- project_id
- slide_id
- score
- issues_json
- auto_fixable
- created_at

---

# 10. 中间产物（Artifacts）设计

## 10.1 requirement_brief

```json
{
  "project_id": "proj_001",
  "goal": "向管理层解释系统架构与投入价值",
  "audience": "CTO/产品负责人",
  "tone": "专业、决策导向",
  "constraints": {
    "max_pages": 12,
    "must_include": ["流程图", "系统架构图", "ROI"],
    "forbidden": ["过度学术化"]
  }
}
```

## 10.2 research_pack

```json
{
  "project_id": "proj_001",
  "topics": [
    {
      "name": "工作流编排",
      "facts": ["多阶段任务可回退", "支持逐页并发"],
      "sources": ["src_1", "src_2"]
    }
  ]
}
```

## 10.3 outline

```json
{
  "project_id": "proj_001",
  "version": 1,
  "slides": [
    {
      "slide_id": "s1",
      "title": "封面",
      "type": "cover",
      "key_message": "介绍主题"
    },
    {
      "slide_id": "s2",
      "title": "为什么要做多阶段生成",
      "type": "argument",
      "key_message": "一步到位不稳定"
    }
  ]
}
```

## 10.4 slide_plan

```json
{
  "slide_id": "s2",
  "type": "comparison",
  "key_message": "多阶段比一步到位更稳定",
  "blocks": [
    {"id": "b1", "kind": "headline", "priority": 10, "text": "为什么要分阶段生成"},
    {"id": "b2", "kind": "left_panel", "priority": 8, "text": "一步到位的问题"},
    {"id": "b3", "kind": "right_panel", "priority": 8, "text": "分阶段的优势"}
  ],
  "layout_intent": {
    "pattern": "two_column_compare",
    "density": "medium",
    "visual_focus": "comparison"
  }
}
```

## 10.5 design_spec

```json
{
  "slide_id": "s2",
  "canvas": {"width": 1280, "height": 720},
  "theme": {
    "bg": "#0B1020",
    "accent": "#5B8CFF",
    "text_primary": "#FFFFFF"
  },
  "layout": {
    "cards": [
      {"id": "c1", "x": 40, "y": 40, "w": 1200, "h": 100, "role": "headline"},
      {"id": "c2", "x": 40, "y": 170, "w": 570, "h": 470, "role": "left_panel"},
      {"id": "c3", "x": 670, "y": 170, "w": 570, "h": 470, "role": "right_panel"}
    ]
  }
}
```

## 10.6 review_report

```json
{
  "slide_id": "s2",
  "score": 0.88,
  "issues": [
    {
      "type": "text_overflow",
      "severity": "medium",
      "message": "右栏第二条文案超过安全区"
    }
  ],
  "auto_fixable": true
}
```

---

# 11. 状态机设计

## 11.1 项目级状态机

```text
draft
→ briefing
→ brief_confirmed
→ researching
→ outline_generating
→ outline_ready
→ planning
→ design_generating
→ rendering
→ reviewing
→ ready_for_edit
→ exporting
→ completed
→ failed
```

## 11.2 页面级状态机

```text
queued
→ planned
→ designed
→ rendered
→ reviewed
→ repaired
→ approved
→ exported
```

要求：

- 项目状态用于总进度显示
- 页面状态用于单页并发与局部重跑

---

# 12. API 设计

## 12.1 项目 API

- `POST /api/projects`
- `GET /api/projects/{id}`
- `PATCH /api/projects/{id}`
- `DELETE /api/projects/{id}`

## 12.2 Brief API

- `POST /api/projects/{id}/brief/generate`
- `PATCH /api/projects/{id}/brief`
- `POST /api/projects/{id}/brief/confirm`

## 12.3 Research API

- `POST /api/projects/{id}/research/run`
- `GET /api/projects/{id}/research`

## 12.4 Outline API

- `POST /api/projects/{id}/outline/generate`
- `GET /api/projects/{id}/outline`
- `PATCH /api/projects/{id}/outline`
- `POST /api/projects/{id}/outline/reorder`

## 12.5 Slide API

- `POST /api/projects/{id}/slides/{slideId}/plan/generate`
- `POST /api/projects/{id}/slides/{slideId}/design/generate`
- `POST /api/projects/{id}/slides/{slideId}/render`
- `POST /api/projects/{id}/slides/{slideId}/review`
- `POST /api/projects/{id}/slides/{slideId}/retry`
- `GET /api/projects/{id}/slides/{slideId}`

## 12.6 批量任务 API

- `POST /api/projects/{id}/generate-all`
- `POST /api/projects/{id}/review-all`
- `POST /api/projects/{id}/export`

## 12.7 任务状态 API

- `GET /api/jobs/{jobId}`
- `GET /api/projects/{id}/progress`
- `WS /ws/projects/{id}/jobs`

---

# 13. 页面类型体系（Slide Taxonomy）

必须建立页面类型体系，避免让模型自由发挥。

建议最少包括：

- cover
- agenda
- section_break
- argument
- key_metrics
- comparison
- timeline
- roadmap
- architecture
- process_flow
- case_study
- quote
- closing

每种类型应定义：

- 允许出现的 block 类型
- 推荐布局模式
- 字数上限
- 视觉优先级
- 是否允许图表
- 是否允许双栏/三栏

---

# 14. 布局引擎设计

## 14.1 原则

不要让模型完全控制几何布局。

应该拆成三层：

1. 大模型生成语义结构
2. 布局引擎计算坐标与尺寸
3. 渲染器生成 SVG

## 14.2 推荐布局模式

- hero_top_plus_cards
- two_column_compare
- three_metric_cards
- timeline_horizontal
- timeline_vertical
- left_diagram_right_text
- top_summary_bottom_grid
- section_cover

## 14.3 输入与输出

输入：

- slide type
- block list
- block priority
- density
- visual focus

输出：

- x/y/w/h
- padding
- safe area
- text bounds
- chart bounds

---

# 15. 渲染策略

## 15.1 核心建议

采用以下路径：

```text
LLM -> design_spec.json -> Renderer -> SVG -> Preview/Export
```

不要采用：

```text
LLM -> 最终自由 SVG
```

原因：

- 不稳定
- 难校验
- 难修复
- 难回滚

## 15.2 Renderer 职责

- 解析 design_spec
- 生成 SVG
- 生成缩略图 PNG
- 检测越界
- 检测重叠
- 生成页面预览文件

---

# 16. 质量控制体系

必须实现独立 Review Engine。

## 16.1 Schema 校验

- JSON 结构是否合法
- 字段是否完整
- 枚举值是否合法

## 16.2 内容校验

- 标题是否过空
- 页面是否重复
- 字数是否过多
- 逻辑是否偏离主题

## 16.3 布局校验

- 是否重叠
- 是否溢出
- 是否留白不足
- 是否视觉主次不清晰

## 16.4 叙事校验

- 目录与正文是否一致
- 首尾是否闭环
- 章节跳转是否合理

## 16.5 品牌校验

- 是否使用非法颜色
- 是否字体不统一
- 是否违背主题系统

---

# 17. 前端页面结构

至少实现以下页面：

## 17.1 项目首页

- 最近项目
- 新建项目
- 模板入口

## 17.2 项目配置页

- 标题
- 主题
- 受众
- 页数
- 风格
- 调研开关

## 17.3 Brief 页

- AI 追问
- 用户回答
- 最终 Brief 预览
- 确认按钮

## 17.4 大纲编辑页

- 数字便利贴视图
- 拖拽排序
- 改标题
- 删除/新增页面

## 17.5 策划页

- 每页 block 结构
- 页面类型切换
- 布局模式切换
- 内容重点调整

## 17.6 设计预览页

- 缩略图列表
- 单页大图预览
- review 报告
- 单页重跑

## 17.7 导出页

- 导出格式选择
- 导出目录选择
- 打开本地目录
- 历史导出记录

---

# 18. 开发顺序

## 阶段 1：最小可跑通链路

目标：快速打通从输入需求到导出 PDF 的全链路。

步骤：

1. 初始化 monorepo
2. 初始化 Electron
3. 初始化 FastAPI
4. 建 PostgreSQL 数据表
5. 实现项目创建
6. 实现 brief 生成
7. 实现 outline 生成
8. 实现简单 slide_plan 生成
9. 实现固定模板 Renderer
10. 实现 PDF 导出

## 阶段 2：可编辑与可重跑

1. 大纲编辑器
2. 单页策划重跑
3. 单页设计重跑
4. 版本记录
5. 质量检查
6. review report 展示

## 阶段 3：工程化增强

1. Model Router
2. 缓存与成本统计
3. 并发任务控制
4. 失败恢复
5. 更丰富布局引擎
6. PPTX 导出

## 阶段 4：商业化准备

1. 账号体系
2. 云同步（可后续再做）
3. 品牌主题系统
4. 团队能力
5. 配额与计费

---

# 19. 让大模型参与开发的方式

不要让大模型一次生成整个系统。

应该采用以下方式：

## 19.1 文档先行

先让模型生成或协助完善：

- PRD
- 架构文档
- API 合约
- Artifact Schema
- Prompt Contract
- 状态机定义

## 19.2 测试先行

让模型先写：

- Schema Tests
- API Contract Tests
- Renderer Golden Tests
- Workflow Integration Tests

## 19.3 模块分治

每次只让模型处理一个明确模块，例如：

- Requirement Agent
- Outline Schema
- Slide Plan Generator
- Review Engine
- FastAPI Router
- Electron Preload Bridge

## 19.4 适合交给模型写的内容

- Schema
- CRUD API
- 单元测试
- Prompt 模板
- 状态机枚举
- SQLAlchemy Models
- Pydantic Models
- Electron 样板代码

## 19.5 不适合完全放手给模型的内容

- 安全边界
- 文件系统权限控制
- 导出链路
- 复杂布局算法
- 稳定性与恢复策略
- 成本控制与资源调度

---

# 20. 仓库结构建议

```text
deckflow/
  apps/
    desktop/                 # Electron App
    api/                     # FastAPI API
    worker/                  # 后台任务执行器
  packages/
    domain/                  # 通用实体与枚举
    schemas/                 # pydantic / zod schema
    prompts/                 # prompt templates
    layout_engine/           # 布局规则
    renderer/                # design_spec -> svg
    exporter/                # svg -> pdf/pptx
    review_engine/           # 质量检查
    model_router/            # 模型路由
  storage/                   # 本地文件系统存储根目录
  scripts/
  docs/
    prd.md
    architecture.md
    artifact-spec.md
    api-contract.md
    prompt-contract.md
```

---

# 21. 开发任务清单（可直接分配给大模型）

## 任务 1：初始化后端

目标：

- 建立 FastAPI 项目
- 接入 PostgreSQL
- 建立 SQLAlchemy / Pydantic 基础结构

输出：

- 项目骨架
- 配置模块
- DB 模块
- 健康检查接口

## 任务 2：初始化 Electron

目标：

- 建立 Electron + React 基础项目
- 配置 main / preload / renderer
- 建立安全 IPC 白名单

输出：

- 基础窗口
- 路由
- 本地 API bridge

## 任务 3：项目 CRUD

目标：

- 实现 projects 表
- 实现创建/更新/读取/删除接口
- 前端接入项目管理页

## 任务 4：Brief 生成模块

目标：

- 实现 Requirement Agent
- 保存 brief artifact
- 支持用户编辑与确认

## 任务 5：Outline 生成模块

目标：

- 实现 Outline Agent
- 产出 outline JSON
- 支持大纲拖拽与编辑

## 任务 6：Slide Plan 生成模块

目标：

- 定义 slide plan schema
- 实现逐页策划生成
- 支持单页重跑

## 任务 7：Design Spec + Renderer

目标：

- 定义 design spec schema
- 编写 SVG renderer
- 生成预览缩略图

## 任务 8：Review Engine

目标：

- 检查溢出、重叠、字号过小
- 输出结构化 review report
- 支持自动修复接口

## 任务 9：导出系统

目标：

- 导出 PDF
- 导出 PPTX
- Electron 选择本地目录并保存

## 任务 10：版本与历史

目标：

- artifact 版本记录
- 导出历史记录
- 支持查看旧版本

---

# 22. 最终原则总结

1. 不要做成一次生成最终页面的黑盒。
2. 必须显式保存每个阶段的中间产物。
3. 大模型负责语义结构，不负责最终确定性执行。
4. 渲染必须走代码引擎，不要完全自由生成最终 SVG。
5. 文件使用本地文件系统保存。
6. PostgreSQL 负责元数据、状态、索引、版本信息。
7. 必须支持单页重跑与局部修复。
8. 必须支持版本追踪与回滚。
9. 先做稳，再做炫。
10. 先打通最短链路，再逐步增强工程能力。

---

# 23. 可直接给大模型的开发指令

你可以把下面这段直接交给大模型作为开发总指令：

```text
请基于本文档，为一个 Electron + Python + PostgreSQL 的 AI PPT 生产系统生成工程实现方案。
要求如下：
1. Electron 负责桌面 UI、本地文件操作桥接、导出目录选择。
2. Python 使用 FastAPI 作为 API 层。
3. 数据库存储使用 PostgreSQL。
4. 所有文件、导出结果、中间产物统一存储到本地文件系统，不使用云对象存储。
5. 系统必须包含 Requirement Agent、Research Agent、Outline Agent、Planning Agent、Design Agent、Review Agent。
6. 生成流程必须分阶段：brief -> research -> outline -> slide_plan -> design_spec -> render -> review -> export。
7. 必须支持 artifact 版本管理、单页重跑、局部修复。
8. 请优先输出：
   - 项目目录结构
   - 数据库表设计
   - Pydantic schema
   - FastAPI 路由设计
   - Electron 前端页面结构
   - 核心工作流代码骨架
9. 请不要直接生成一个黑盒系统，而要保持模块清晰、可测试、可扩展。
```

