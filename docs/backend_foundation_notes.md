# 后端基础补充说明

更新日期：2026-04-09

## 1. 数据库简表

当前后端已补充最小数据库模型，目标是先把项目元数据和 artifact 索引稳定落库。

### `projects`

- `id`：项目主键
- `title`：项目标题
- `topic`：用户输入的主题与需求原文
- `status`：项目状态
- `created_at`：创建时间
- `updated_at`：更新时间

### `project_configs`

- `project_id`：关联 `projects.id`
- `scenario`：使用场景
- `audience`：受众
- `style_pref`：风格偏好
- `page_limit`：页数上限
- `research_enabled`：是否启用 research
- `narration_enabled`：是否启用讲稿

### `artifact_records`

- `id`：自增主键
- `project_id`：关联 `projects.id`
- `artifact_type`：`research / brief / outline` 等
- `version`：版本号
- `storage_path`：本地文件路径
- `created_at`：记录时间

说明：

- 当前仍以本地文件系统为 artifact 主存储。
- 数据库负责项目索引、配置和 artifact 版本索引。
- schema 在应用启动时可自动创建，适合当前 MVP 阶段。

## 2. 模型接口

后端已补充统一的 Model Router，支持两类 provider：

- OpenAI
- Gemini

### OpenAI

- 默认基于 `Responses API`
- 配置项：
  - `PPT_AGENT_OPENAI_BASE_URL`
  - `PPT_AGENT_OPENAI_API_KEY`
  - `PPT_AGENT_OPENAI_MODEL`

### Gemini

- 默认基于 `models.generateContent`
- 配置项：
  - `PPT_AGENT_GEMINI_BASE_URL`
  - `PPT_AGENT_GEMINI_API_KEY`
  - `PPT_AGENT_GEMINI_MODEL`

### 统一接口

新增 API：

- `GET /api/models/providers`
- `POST /api/models/generate`

用途：

- 查询 provider 配置状态
- 用统一请求体直接测试 OpenAI / Gemini 文本生成

## 3. 当前边界

当前这层能力解决的是：

- 数据库最小落地
- provider 抽象
- OpenAI / Gemini 统一调用入口

还没有做的部分：

- 真正的 prompt 模板分层
- research / brief / outline 对模型的正式调用
- provider 级重试、限流、fallback
- 数据库 migration 脚本与 Alembic 版本管理
