# mi-book-writer 可视化 Dashboard 设计

## 背景

`mi-book-writer` 当前是 CLI 驱动的多 Agent 写书系统，核心能力已经具备：

- 通过 `BookWriterGraph` 执行 `init → indexing → planning → writing → final_review → output` 工作流。
- 通过 SQLite checkpoint 保存执行状态，支持继续执行、局部章节修复、重新生成输出。
- 通过 ChromaDB 保存 RAG 索引，状态可通过 `status` 命令查看。
- 通过 `logs/book-writer.log` 持久化运行日志。
- 通过 `output/` 生成结构化 Markdown 书稿。

当前缺口是运行过程不可视：用户只能看 CLI 日志和 JSON 状态，难以判断系统卡在哪、慢在哪、哪章质量不过、当前书稿长什么样。

## 目标

新增一个专业前后端分离 Dashboard，用于观察、控制和审阅写书过程，同时不降低现有写作质量流程。

Dashboard 必须支持：

1. 实时查看运行状态、当前节点、当前章节、完成进度。
2. 查看各 Agent 的阶段耗时、重试、质量反馈和异常。
3. 查看 RAG 索引健康状态、chunk 数、参考书索引状态。
4. 查看章节树、Markdown 预览、章节质量反馈。
5. 查看实时日志，并按级别、Agent、章节过滤。
6. 执行安全操作：启动、继续、重新生成 output、局部修订章节、导出状态。
7. 对危险操作做显式确认：reset、fresh run、覆盖章节。

## 非目标

本阶段不做以下内容：

- 不把写书核心逻辑搬到前端。
- 不改变现有高质量写作流程，不减少事实核查、风格校验、审校环节。
- 不做多人协作、账号系统、权限系统。
- 不做云端部署或公网访问。
- 不做富文本在线编辑器，章节修改仍以 Markdown 文本为基础。
- 不强行重构 `BookWriterGraph` 核心业务，只补必要的 API 适配层。

## 技术栈

### 后端

- `FastAPI`
- `uvicorn`
- `pydantic`
- WebSocket，必要时提供 SSE 兼容接口
- 复用现有 `BookWriterGraph`、`BookState`、日志文件、checkpoint、output 目录

### 前端

- `Vue 3`
- `Vite`
- `TypeScript`
- `Naive UI`
- `ECharts`
- `markdown-it`

## 目录结构

```text
book-writer/
├── api/
│   ├── __init__.py
│   ├── app.py              # FastAPI app 工厂
│   ├── models.py           # API DTO
│   ├── services.py         # Dashboard 查询与命令服务
│   ├── events.py           # WebSocket/SSE 事件流
│   └── log_reader.py       # 日志 tail 与解析
├── web/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── api/
│       ├── components/
│       ├── pages/
│       ├── stores/
│       └── styles/
├── core/
├── agents/
├── graph/
└── cli.py
```

`core/`、`agents/`、`graph/` 继续作为写书领域核心。`api/` 只做适配，不直接承载写作业务。

## 后端 API 设计

### 状态与指标

- `GET /api/status`
  - 返回 thread 状态、phase、next nodes、当前章节、已写章节数、总章节数、RAG 健康状态。
- `GET /api/metrics`
  - 从日志和 checkpoint 聚合耗时指标。
  - 返回每章耗时、每 Agent 平均耗时、修订次数、错误次数。
- `GET /api/rag/status`
  - 返回 ChromaDB chunk 数、manifest 状态、books 目录状态、索引是否健康。

### 章节与输出

- `GET /api/chapters`
  - 返回全书章节树、每章状态、是否已写、字数、反馈摘要。
- `GET /api/chapters/{chapter_id}`
  - 返回章节 Markdown、标题、状态、事实反馈、风格反馈、审校反馈。
- `GET /api/output/files`
  - 返回 `output/` 文件树。
- `GET /api/output/file?path=...`
  - 返回指定输出 Markdown 内容，路径必须限制在 `output/` 内。

### 日志

- `GET /api/logs?level=&agent=&chapter=&limit=`
  - 返回过滤后的日志片段。
- `WS /api/events`
  - 推送状态变化、日志新增、章节更新、指标刷新。

### 操作

- `POST /api/run`
  - 启动或继续当前 thread。
- `POST /api/resume`
  - 从 checkpoint 继续。
- `POST /api/regenerate-output`
  - 根据 checkpoint 重新生成 `output/`。
- `POST /api/chapters/{chapter_id}/patch`
  - 用 Markdown 覆盖指定章节正文。
- `POST /api/chapters/{chapter_id}/revise`
  - 按用户反馈触发局部 LLM 修订。
- `POST /api/export-state`
  - 导出 checkpoint 状态。
- `POST /api/reset`
  - 危险操作，必须要求确认字段，例如 `{ "confirm": "RESET book-1" }`。

## 前端页面设计

### 1. 总览页

展示卡片：

- 当前任务：thread id、phase、next node。
- 当前章节：章节 ID、标题、所在篇章、当前 Agent。
- 进度：已完成章节 / 总章节，百分比环形进度。
- 健康状态：checkpoint、RAG、output、日志。
- 预计剩余时间：基于最近章节平均耗时计算。

图表：

- 章节完成趋势。
- Agent 阶段耗时堆叠柱状图。
- 最近错误和重试次数。

### 2. 运行流页面

以流程图或时间线展示：

```text
Planner → Research → Writer → FactChecker → Revision → StyleGuard → Editor → Director → Output
```

每个节点显示：

- 状态：pending、running、passed、failed、skipped。
- 最近开始时间、结束时间、耗时。
- 当前章节和反馈摘要。

### 3. 章节审阅页

布局：

- 左侧：篇章/章节树。
- 中间：Markdown 预览。
- 右侧：质量面板。

质量面板包括：

- 字数。
- 状态。
- 事实核查反馈。
- 风格反馈。
- 审校反馈。
- 修订次数。
- 操作按钮：局部修订、覆盖章节、重新生成 output。

### 4. 日志页

能力：

- 实时滚动日志。
- 按级别过滤：INFO、WARNING、ERROR。
- 按 Agent 过滤：Planner、Research、Writer、FactChecker、StyleGuard、Editor、Director。
- 按章节过滤。
- 支持暂停自动滚动。

### 5. 指标页

展示：

- 每章总耗时。
- 每 Agent 平均耗时。
- 最慢章节排行。
- 修订次数排行。
- RAG 检索耗时趋势。
- LLM 调用耗时趋势。

### 6. 设置页

展示只读配置：

- 当前配置目录。
- 输出目录。
- books 目录。
- LLM provider/model，API Key 只显示是否已配置，不显示明文。
- 日志文件路径和轮转配置。

## 状态来源

Dashboard 聚合以下来源：

1. `BookWriterGraph.get_status(thread_id)`：权威运行状态。
2. checkpoint 中的 `BookState`：章节树、章节正文、反馈、当前章节。
3. `logs/book-writer.log`：阶段耗时、事件流、错误信息。
4. `.data/chroma` 和 manifest：RAG 健康状态。
5. `output/`：最终 Markdown 文件树和预览。

## 运行模型

后端需要避免同一 thread 同时启动多个写作任务。

设计：

- 维护内存级运行锁：`thread_id -> running task`。
- `POST /api/run` 如果已有任务运行，返回当前运行状态，不重复启动。
- 写作任务在后台线程或 asyncio task 中执行。
- WebSocket 每 1 秒推送一次状态快照，并推送新增日志行。
- CLI 和 Web 共用 checkpoint；如果 CLI 正在跑，Web 仍可观察，但不应再启动同一 thread。

## 安全设计

- 默认只监听 `127.0.0.1`。
- 不提供公网部署配置。
- 所有文件读取 API 必须做路径约束，禁止读取项目外文件。
- `.env`、API Key、token 永远不返回前端。
- reset、fresh run、patch chapter 必须二次确认。
- 日志展示时对疑似密钥做脱敏。

## 质量保障

### 后端测试

- API status 返回结构测试。
- output 文件路径越界防护测试。
- 日志解析过滤测试。
- 运行锁测试。
- reset 确认字段测试。

### 前端测试

- TypeScript 类型检查。
- 关键组件渲染测试可后续加入；本阶段至少保证 build 通过。

### 验证命令

后端：

```bash
uv run pytest
uv run ruff check .
uv run mypy --python-version 3.14 core agents graph api cli.py main.py
```

前端：

```bash
cd web
pnpm install
pnpm build
```

## 分阶段实施

### Phase 1：后端只读 API

- 引入 `FastAPI`、`uvicorn`。
- 新增 `api/`。
- 实现 status、chapters、chapter detail、logs、output files、rag status。
- 增加后端测试。

### Phase 2：前端基础 Dashboard

- 初始化 `web/`。
- 实现布局、路由、总览页、章节审阅页、日志页。
- 接入只读 API。
- 实现 Markdown 预览。

### Phase 3：实时事件与指标

- 实现 WebSocket 事件流。
- 日志 tail。
- 指标聚合。
- ECharts 图表。

### Phase 4：安全操作控制

- 实现 run、resume、regenerate-output。
- 实现 patch/revise chapter。
- 实现 reset 二次确认。
- 增加运行锁。

## 验收标准

1. 本地启动后端和前端后，能在浏览器看到当前 thread 状态。
2. Dashboard 能显示当前章节、总进度、RAG 健康、checkpoint 状态。
3. 能浏览章节树并预览已写 Markdown。
4. 能实时查看日志。
5. 能看到每章和每 Agent 的耗时指标。
6. 不泄露 `.env`、API Key、token。
7. 不破坏现有 CLI 工作流。
8. 后端测试、静态检查、前端 build 均通过。

## 设计自检

- 没有使用占位需求；实现边界明确。
- 前后端职责清晰：前端展示与交互，后端适配与安全控制，核心写书逻辑保持在现有模块。
- 方案聚焦本地 Dashboard，没有扩展到账号、权限、公网部署等额外范围。
- 危险操作有确认机制，敏感信息有脱敏要求。
