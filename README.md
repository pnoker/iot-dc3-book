# mi-book-writer

专业多 Agent 书籍写作系统，面向长篇技术书的知识库管理、出版级大纲、三级小节写作、事实核查、风格校验、审校和输出。

## 出版级分阶段流程

当前推荐使用三阶段命令，不再把知识库、大纲和写作绑成一步到位的长链路：

```text
kb      → 管理本地证据库，负责增量索引、显式重建和健康检查
outline → 生成全书大纲 + 每章三级写作单元，人工审阅后 approve
write   → 基于 approved outline 按 1.1.1 小节级 checkpoint 续写
```

核心产物：

- `.data/chroma`、`.data/rag_index.json`、`.data/bm25_index.json`：知识库索引。
- `.data/outlines/current.json`：可审阅、可导出的当前大纲。
- `.data/outlines/approved.json`：写作阶段唯一读取的已批准大纲。
- `.data/write/<thread-id>.json`：小节级写作 checkpoint。
- `.data/manuscript/chapter-XX/<section-id>.md`：三级小节中间稿，例如 `1.1.1.md`。
- `output/`：最终导出的章节级出版稿。

### 从零开始

第一次跑出版级流程时，按下面顺序执行。知识库、大纲和写作彼此独立，任何一步失败都只需要重跑该阶段。

```bash
# 1. 检查知识库状态
uv run python main.py kb status

# 2. 构建/更新知识库；默认增量，不会无脑重建
uv run python main.py kb build

# 3. 生成出版级大纲和 1.1.1 级别写作单元
uv run python main.py outline generate

# 4. 导出大纲给人工审阅；可直接编辑导出的 JSON
uv run python main.py outline export --file ./drafts/outline.json

# 5. 批准大纲；以下两条二选一
# 5.1 未人工编辑时，批准 .data/outlines/current.json
uv run python main.py outline approve

# 5.2 如果你编辑了导出的 JSON，则批准指定文件
uv run python main.py outline approve --source ./drafts/outline.json

# 6. 初始化小节级写作 checkpoint
uv run python main.py write start

# 7. 每次只写一个或少量三级小节，便于审稿和中断恢复
uv run python main.py write resume --max-sections 1
```

### 日常续写

写作阶段的恢复单位是三级小节，例如 `1.1.1`。程序中断后，不需要重新生成大纲，也不需要重建知识库。

```bash
# 查看当前写作断点
uv run python main.py write status

# 查看小节级目录与完成状态
uv run python main.py write contents

# 从当前小节继续写 1 个小节
uv run python main.py write resume --max-sections 1

# 一次写 3 个小节；建议确认质量稳定后再调大
uv run python main.py write resume --max-sections 3

# 查看某个已写小节
uv run python main.py write section 1.1.1

# 导出当前已组装章节到 output/
uv run python main.py write export-output
```

### 人工审稿与局部修复

小节中间稿是 `.data/manuscript/chapter-XX/<section-id>.md`。人工修改后必须回写到小节级 checkpoint，否则只改文件不会改变写作状态。

```bash
# 查看并编辑小节中间稿
$EDITOR .data/manuscript/chapter-01/1.1.1.md

# 回写小节；如果该章所有小节已完成，会自动重新合成章节
uv run python main.py write patch-section --section-id 1.1.1 --file .data/manuscript/chapter-01/1.1.1.md

# 回写后查看断点和统计
uv run python main.py write status

# 需要出版稿时再导出 output/
uv run python main.py write export-output
```

### 重建与覆盖规则

默认命令都尽量避免破坏已有产物；会覆盖或重建的操作必须显式加参数。

```bash
# 全量重建知识库：会清空 Chroma/BM25/manifest 后重新索引
uv run python main.py kb build --rebuild

# 覆盖当前大纲 current.json
uv run python main.py outline generate --force

# 覆盖当前 thread-id 的小节级写作 checkpoint
uv run python main.py write start --fresh
```

注意：`output/` 是导出结果，不是源数据；当前真实写作进度以 `.data/write/<thread-id>.json` 和 `write status` 为准。

## 代码结构

```text
agents/              # 各写书 Agent 的提示词与调用封装
core/                # 状态、配置、LLM、RAG、输出等基础能力
config/              # 书籍、章节、风格、模型和输出配置
tests/               # 状态、工作流、CLI、RAG、LLM 等回归测试
cli.py               # Typer CLI 命令定义与分发
main.py              # 最小入口
```

`core/workflow.py` 是当前 CLI 使用的三阶段编排入口：

- `kb_*`：知识库状态检查、增量构建和显式重建。
- `outline_*`：出版级大纲生成、导出和批准。
- `write_*`：小节级 checkpoint、续写、局部回写和导出。

`core/` 的 RAG 能力已拆分：

- `rag_pdf.py`：基于 `pymupdf4llm` 的 PDF Markdown 提取。
- `rag_chunking.py`：基于 `langchain-text-splitters` 的文本分块。
- `rag_manifest.py`：索引输入签名与过期判断。
- `rag.py`：RAGEngine 编排 ChromaDB 与检索。
- `web_research.py`：抓取显式配置的在线 URL，作为可选证据补充。

### 知识库与证据层

本地向量知识库定位为“证据层”，不是自动写作的万能素材池：

- RAG 索引会根据来源文件路径、大小、`mtime_ns`、chunk 配置和 embedding 模型生成 manifest；源文件变化后，下次 `kb build` 会增量更新新增、修改和删除的文件。
- 只有 `kb build --rebuild` 会清空并全量重建知识库；写作恢复不会隐式重建知识库。
- `ResearchDossier` 会给本地证据编号为 `[S1]`、在线证据编号为 `[W1]`，写作与引用守门都以这些证据为硬事实依据。
- `references.web_research` 默认关闭；启用后只抓取显式配置的 URL，不做无来源网络搜索。

```yaml
web_research:
  enabled: true
  urls:
    - "https://example.com/report"
```

若需要接入 SaaS 知识库或搜索服务，可在该层后续扩展为 Pinecone、Qdrant Cloud、Weaviate Cloud、Zilliz Cloud、Elastic Cloud、Azure AI Search 或 Supabase pgvector。

`core/templates/` 存放 Jinja2 Markdown 输出模板，封面、作者简介、导读、目录、附录和伏笔报告均通过模板渲染。

配置先解析 YAML 中的 `${VAR}` 环境变量占位符，再一次性加载为强类型 `AppConfig`：

- 未知 YAML 字段会直接报错，避免配置拼写错误静默失效。
- `.env` 固定从项目根目录读取，shell 环境变量仍可覆盖 `.env`。
- `references.sources[*].path` 和 `output.dir` 都相对项目根目录解析；参考来源必须显式配置。
- checkpoint、RAG 索引和 manifest 固定写入 `.data/`。

## 环境变量

不要把 API Key 明文写入 YAML 配置文件。`config/llm.yaml` 只写环境变量占位符，例如 `api_key: "${DEEPSEEK_API_KEY}"`。复制 `.env.example` 为 `.env`，再填写本地密钥：

```bash
cp .env.example .env
# 编辑 .env：
# DEEPSEEK_API_KEY=...
# OPENROUTER_API_KEY=...
```

也可以在 shell 中用同名环境变量临时覆盖 `.env`；只有 YAML 中显式写了 `${VAR}` 的字段才会被替换。缺失或空值变量会在配置加载阶段直接报错。

## 运行方式

项目不包含前端界面或本地 HTTP API。状态查看、章节修复、输出重生成等操作均通过 CLI 命令完成。

默认日志会持久化到 `logs/book-writer.log`，单文件 `10MB`，保留 `10` 个历史分片。可按需调整：

```bash
uv run python main.py --log-file logs/run.log --log-max-bytes 5242880 --log-backup-count 5 write resume --max-sections 1
```

## 验证

```bash
uv run ruff check .
uv run pytest
uv run mypy --python-version 3.14 core agents cli.py main.py
```
