# DeckFlow 实施计划

更新日期：2026-04-09

## 1. 文档目的

本文基于 [`deckflow_prd_architecture_cn.md`](./deckflow_prd_architecture_cn.md) 提炼出一份面向当前仓库的可执行实施计划，用于指导接下来 `Electron + Python + PostgreSQL + 本地文件系统` 的落地顺序。

同时参考了一篇外部实践分享：

- Linux.do，Sandun，2026-03-19，《应该是目前最强的PPT Agent，附上完整思路分享》：https://linux.do/t/topic/1782304

这份计划不重复 PRD 全文，而是回答四个问题：

1. DeckFlow 的 MVP 到底要先做成什么。
2. 当前仓库距离目标还缺什么。
3. 应该按什么顺序实现，才能尽快打通最短链路。
4. 每个阶段的完成标准是什么。

## 2. 对帖子路线的核心理解

### 2.1 产品本质

DeckFlow 应严格按帖子的方法去做：先让 AI 像顾问一样调研和追问，再整理数字便利贴式大纲，再为每页写策划稿，最后由强模型直接生成整页 SVG。

它的核心价值是：

- 先把内容方向问准
- 先把页面逻辑排清楚
- 让模型在高质量上下文里直接出专业页面
- 结果天然适合预览、导出和后续编辑
- 前端体验必须足够丝滑，不能做成“功能能用但操作发涩”的工具

### 2.2 MVP 的真正边界

MVP 的最小闭环应该是：

1. 创建项目
2. AI 联网调研并追问需求
3. 生成并确认 brief
4. 生成数字便利贴式 outline
5. 逐页生成 slide plan
6. 逐页直接生成 SVG
7. 生成预览与缩略图
8. 支持单页重跑
9. 导出 SVG / PDF
10. PPTX 作为后续增强

### 2.3 技术上的关键约束

严格按帖子路线时，最重要的技术决定有五个：

- 前端负责顾问式交互、大纲便利贴编辑、SVG 预览和导出。
- 后端负责搜索、追问、工作流、模型调用、SVG 生成和文件落盘。
- 设计阶段的核心产物就是 SVG，不再以 `design_spec -> renderer` 作为主路线。
- 首版布局方法以卡片式 / Bento Grid 为主，而不是先做复杂代码布局引擎。
- 文件内容保存在本地文件系统，数据库保存项目、状态、版本和产物索引。

### 2.4 必须采纳的帖子结论

- 需求追问必须建立在搜索和背景理解之上，不能只靠静态表单。
- 大纲编辑必须强交互化，优先采用数字便利贴。
- 策划稿是核心中间层，不能省略。
- 页面设计首版直接生成整页 SVG。
- SVG 的编辑性和与 Office 的兼容性，是这条路线成立的重要原因。

## 3. 当前仓库现状

当前仓库已经是一个 monorepo，保留了两个固定目录名：

- `ppt-agent/`：Python 后端
- `ppt-agent-desktop/`：Electron 前端

当前已有的基础工作：

- 根目录仓库规范文件已存在：`.editorconfig`、`.gitignore`、`.gitattributes`
- 后端已完成 `uv` 基础初始化，存在 `pyproject.toml`、`uv.lock`、最小启动入口
- 前端已完成 Electron 最小入口初始化，存在 `package.json` 和 `src/main.js`

当前与目标相比的主要缺口：

- 后端还没有 FastAPI、数据库层、任务编排层、模型路由层
- 前端还没有 preload、renderer、页面路由、状态管理
- 还没有 PostgreSQL 数据模型
- 还没有本地 `storage/` 目录约定和 file service
- 还没有 artifact schema、状态机枚举、API 合约
- 还没有搜索接入、SVG 生成链路、导出链路

## 4. 实施总原则

### 4.1 先把帖子主链路做出来

第一优先级不是做最漂亮的页面，而是先跑通：

`调研 -> 追问 -> brief -> 便利贴大纲 -> slide plan -> 直接 SVG -> export`

### 4.2 任何阶段都要落盘

以下内容必须是明确文件，而不是只存在内存里：

- requirement_brief
- research_pack
- outline
- slide_plan
- svg_slide
- preview 结果
- review_report
- export 结果

### 4.3 先把 prompt 资产做扎实

帖子路线高度依赖 prompt 设计，所以首版必须优先沉淀：

- 搜索总结 prompt
- 追问 prompt
- 大纲生成 prompt
- 策划稿 prompt
- SVG 设计 prompt
- 卡片式 / Bento Grid 布局提示词

### 4.4 SVG 是主产物，不是附属格式

首版设计阶段的主输出就是整页 SVG。代码侧主要负责：

- SVG 基础合法性检查
- 预览图生成
- 导出适配
- Office 兼容性增强

### 4.5 MVP 工作流先用简化版

当前仓库更适合先采用 PRD 中的“方案 A”：

- FastAPI
- PostgreSQL
- 内部任务队列
- 数据库状态表

等 MVP 稳定后，再考虑升级为更强的持久化工作流方案。

## 5. 推荐目标结构

在不改现有两个顶层目录名的前提下，建议逐步演进为下面的结构：

```text
ppt-agent/
  src/ppt_agent/
    api/
    core/
    db/
    domain/
    workflows/
    agents/
    services/
    prompts/
    search/
    svg/
    preview/
    exporter/
  tests/

ppt-agent-desktop/
  src/
    main/
    preload/
    renderer/
      app/
      pages/
      components/
      stores/
      services/
      types/

docs/
storage/
```

说明：

- `storage/` 放在仓库根目录，便于开发期统一查看本地产物
- 后端应显式区分搜索、prompt、SVG、预览和导出
- 前端应尽快从单文件 Electron 入口升级为 `main + preload + renderer` 三层结构

## 6. 分阶段实施计划

## 阶段 0：基础工程定型

目标：把“能按帖子路线持续迭代”所需的基础设施先搭起来。

后端任务：

- 接入 FastAPI、SQLAlchemy、Pydantic、Alembic
- 增加配置模块，统一管理数据库、模型、搜索服务、存储根目录
- 增加健康检查接口
- 建立基础日志方案
- 建立 prompt 目录和版本管理方式

前端任务：

- 将 Electron 拆分为 `main`、`preload`、`renderer`
- 选定 renderer 技术栈，建议 `React + TypeScript + Vite`
- 建立基础路由和页面壳
- 建立 IPC 白名单与后端 API 调用层
- 建立 SVG 预览组件能力
- 明确前端性能预算，优先保证拖拽、切页、缩放、状态更新的流畅度

共享任务：

- 创建 `docs/api-contract.md`、`docs/artifact-spec.md`、`docs/state-machine.md`、`docs/prompt-contract.md`
- 建立 `.env.example`
- 建立 `storage/` 根目录约定

完成标准：

- 前端和后端都能独立启动
- Electron 能打开主窗口并调用后端健康检查
- 后端能连接 PostgreSQL
- Alembic 能成功初始化数据库
- 搜索服务和模型配置可以被统一读取

## 阶段 1：项目域与最小闭环

目标：先把“调研 + 追问 + brief + 便利贴大纲”打通。

后端任务：

- 建立 `projects`、`project_configs`、`workflow_runs` 基础表
- 实现项目 CRUD API
- 定义 `requirement_brief` schema
- 实现联网调研、追问、brief 生成、编辑、确认接口
- 定义 `outline` schema
- 实现 outline 生成、读取、更新、重排接口
- 问题至少覆盖目标、受众、使用场景、必须包含内容、禁用内容

前端任务：

- 项目首页
- 项目配置页
- Brief 页
- 大纲编辑页
- 大纲编辑页优先采用“数字便利贴”视图来呈现页面结构和顺序
- 便利贴拖拽交互必须即时反馈，避免拖拽时重排卡顿

文件与状态任务：

- File Service 建立项目目录
- Artifact Service 保存 `brief`、`outline`
- 建立项目级状态机：`draft -> briefing -> brief_confirmed -> outline_ready`

测试任务：

- 项目 CRUD API contract tests
- brief / outline schema tests
- outline reorder 行为测试
- brief 问题覆盖率与必填约束测试
- research 结果落盘测试

完成标准：

- 用户可以创建项目并完成 brief 确认
- outline 可以生成、展示、编辑和重排
- 中间产物落盘且数据库中可索引
- 用户能明显感受到“AI 先理解需求再开始做 PPT”

## 阶段 2：逐页策划与 SVG 设计稿

目标：从 outline 进入逐页生产，并直接生成可用 SVG。

后端任务：

- 建立 `slides`、`slide_jobs`、`artifacts`、`artifact_versions` 表
- 定义 slide taxonomy
- 定义 `slide_plan` schema
- 实现 Planning Agent
- 实现 SVG Design Agent
- 支持单页生成与批量生成
- 在 `slide_plan` 中显式加入 `key_message`、`blocks`、`layout_intent`、`visual_focus`、`density`
- 沉淀卡片式 / Bento Grid 提示词库
- 选择一款强 SVG 模型作为首版主力模型

前端任务：

- 策划页
- 页面类型切换
- 布局模式切换
- 单页详情侧栏
- 策划页优先体现“先定内容结构，再定视觉风格”的分层逻辑
- 增加 SVG 原稿预览面板
- 切换当前页和查看 SVG 原稿时要做到低延迟、低闪烁

状态任务：

- 建立页面级状态机：`queued -> planned -> svg_generated`
- 支持单页重跑 `plan` 和 `svg`

测试任务：

- slide taxonomy 枚举测试
- slide_plan schema tests
- 单页重跑流程测试
- SVG 基础结构校验测试

完成标准：

- 每页都能生成结构化 `slide_plan`
- 每页都能生成整页 SVG
- 用户可以切换页面类型和局部重跑
- SVG 结果达到“可看、可改、可导出”的最低门槛

## 阶段 3：预览与导出系统

目标：把 SVG 设计稿稳定地变成预览和交付文件。

后端任务：

- 实现 SVG 基础合法性检查
- 生成缩略图 PNG
- 建立预览文件输出规则
- 实现 PDF 导出
- 预留 PPTX / Office 导出适配层
- 建立 SVG 后处理与兼容性增强规则

前端任务：

- 设计预览页
- 缩略图列表
- 单页大图预览
- 页面生成进度展示
- 导出页初版
- 状态刷新尽量局部更新，避免整页重绘造成视觉抖动

测试任务：

- SVG 打开与预览测试
- PDF 导出链路测试
- 典型页面类型 SVG 回归测试
- Office 兼容性抽样测试

完成标准：

- 前端可以查看缩略图和单页预览
- 用户可以导出 SVG / PDF
- 首版兼容路径明确，可继续迭代 Office 导出

## 阶段 4：质量检查与局部修复

目标：把“能看”提升为“可控”和“可修”。

后端任务：

- 定义 `review_report` schema
- 实现 Review Engine
- 检查文本溢出、元素重叠、字号过小、留白不足
- 检查 SVG 结构问题
- 增加自动修复接口，先从简单规则修复开始
- 建立 `review_reports` 表

前端任务：

- review 报告面板
- 单页重跑入口
- 修复建议提示

状态任务：

- 页面状态扩展到 `svg_generated -> previewed -> reviewed -> repaired`
- 项目状态扩展到 `reviewing -> ready_for_edit`

测试任务：

- review schema tests
- 自动修复规则测试
- review 结果展示测试

完成标准：

- 每页都能输出结构化 review 结果
- 用户可以看到问题和修复建议
- 基础问题支持自动修复或定向重跑

## 阶段 5：模板与 Office 兼容增强

目标：解决帖子路线在企业真实场景中的两个难点：模板适配和 Office 兼容。

后端任务：

- 支持从企业模板/主题出发生成
- 优化 SVG 到 Office 的导入表现
- 建立 `exports` 表
- 保存导出历史

前端任务：

- 模板选择入口
- 主题系统配置
- 导出历史与兼容提示

测试任务：

- 模板适配测试
- Office 导入兼容性测试
- 文件存在性与命名规则测试

完成标准：

- 生成结果不只适合“从零设计”，也能贴近企业模板场景
- 导出历史可查询
- Office 兼容问题被收敛到可接受范围

## 阶段 6：工程化增强

目标：把 MVP 提升为稳定可扩展的产品基础。

任务：

- Model Router
- Prompt 版本管理
- 模型成本统计
- 并发任务控制
- 失败恢复
- 更丰富布局模式
- 更强的搜索与资料质量控制
- PPTX 导出正式落地
- 观测、日志、告警

完成标准：

- 可追踪模型调用、成本、耗时、失败原因
- 任务失败后可以恢复或重试
- 关键模块具备可观测性

## 7. 模块拆解优先级

按依赖顺序，建议优先级如下：

1. 后端配置、数据库、基础 API
2. Electron 三层结构和前后端通信
3. 搜索与追问链路
4. 项目 CRUD
5. brief artifact
6. outline artifact
7. slide taxonomy 与 schema
8. slide plan
9. SVG prompt 与 SVG 生成
10. preview / export
11. review
12. model router 与工程化增强

原因：

- `brief` 和 `outline` 是后续所有页面生成的输入基础
- SVG 生成质量高度依赖搜索、追问和策划稿质量
- `review` 和 `export` 都依赖已有 SVG 产物

## 8. 建议的首批数据库实体

第一批必须先落地：

- `projects`
- `project_configs`
- `slides`
- `artifacts`
- `artifact_versions`
- `workflow_runs`
- `slide_jobs`

第二批再补：

- `exports`
- `model_calls`
- `review_reports`
- `users`

原因：

- 首批实体足够支撑 MVP 主链路
- 账号体系不是当前最短路径上的阻塞项

## 9. 建议的首批文档输出

在开始大规模编码前，建议先补齐以下文档：

- `docs/api-contract.md`
- `docs/artifact-spec.md`
- `docs/state-machine.md`
- `docs/storage-layout.md`
- `docs/prompt-contract.md`
- `docs/svg-guidelines.md`

这一步非常关键，因为 DeckFlow 的复杂度主要来自“模块之间的契约”，而不是单个模块内部代码量。

## 10. 风险与前置决策

### 10.1 最大风险

- 搜索和追问做得浅，导致后面页面再漂亮也不专业
- SVG prompt 不稳定，导致输出质量波动大
- 选错模型，导致 SVG 结构质量不够
- 前端状态模型设计不当，导致大纲拖拽和 SVG 预览不丝滑
- 前端过早追求复杂编辑器，拖慢主链路
- 过早做 PPTX 导出，压缩 MVP 进度
- 没有版本化，后期无法支持局部回滚和对比
- 只做“美观生成”，却没有把需求追问和策划层做深，最终导致内容质量不够专业
- 忽略“套现有模板”的真实场景，系统只擅长从零设计，却无法适应企业已有品牌模板和版式规范
- 过度依赖 SVG 直接导入 PowerPoint 的默认表现，忽略 Office 转换细节可能带来的形状失真和兼容性问题

### 10.2 需要尽快拍板的事项

- 前端 renderer 是否采用 React + TypeScript + Vite
- 后端任务队列 MVP 方案是否采用数据库状态表 + 后台 worker
- 本地 `storage/` 根目录放在仓库内还是用户目录
- 首版搜索能力接入哪一家服务
- 首版 SVG 主力模型选择哪一个
- 首版是否启用 research 能力，还是先用 mock research 打通链路
- 首版布局系统是否明确以卡片式/Bento Grid 为第一优先布局语言
- 首版 SVG 产物是否作为预览和 Office 兼容导出的标准形态
- 首版是否支持“从企业现有模板/主题出发”而不是只支持从零生成设计

## 11. 建议的近期执行顺序

如果按当前仓库状态继续推进，建议下一步严格按下面顺序执行：

1. 初始化 FastAPI、数据库连接、Alembic 和健康检查
2. 初始化 Electron 的 preload 和 renderer 工程
3. 接入搜索服务和模型配置
4. 定义项目、brief、outline 的 schema 和 API contract
5. 先设计“需求追问 + 数字便利贴大纲编辑”的交互闭环
6. 打通项目创建、research、brief、outline 生成的端到端链路
7. 补 slides、slide_plan 的 schema
8. 以卡片式/Bento Grid 为起点实现首版 SVG 生成
9. 打通 SVG 预览与 PDF 导出

## 12. 里程碑定义

### M1：项目到大纲闭环

用户可以创建项目、确认 brief、拿到 outline 并编辑。

### M2：页面预览闭环

系统可以对每页生成 `slide_plan`，并直接产出可用 SVG。

### M3：可编辑可重跑闭环

用户可以单页重跑、查看 review、修复基础问题。

### M4：可交付闭环

系统可以导出 SVG / PDF，并保存导出历史。

## 13. 结论

DeckFlow 的实施重点是先忠实复现帖子验证过的方法链路：搜索、追问、便利贴大纲、策划稿、直接 SVG。当前仓库已经完成了 monorepo 的最小初始化，下一阶段应立即进入“后端基础设施 + 搜索与追问 + 便利贴大纲 + 首版 SVG 生成”的建设，而不是先做复杂代码布局引擎。
