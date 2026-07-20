# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

mi-book-writer 是一个面向长篇技术书的多 Agent 出版级写作系统。通过三个阶段完成从知识库到出版稿的全流程：`kb`（知识库索引）→ `outline`（大纲生成与批准）→ `write`（小节级写作与审校）。

## Common Commands

所有命令通过 `uv run python main.py` 执行，全局参数（`--config`、`--thread-id`、`--log-level`）放在子命令之前。

```bash
# 知识库
uv run python main.py kb status          # 索引健康状态
uv run python main.py kb build           # 增量构建
uv run python main.py kb build --rebuild # 全量重建

# 大纲
uv run python main.py outline status     # 大纲状态
uv run python main.py outline generate   # 生成大纲（已存在则拒绝，用 --force 覆盖）
uv run python main.py outline approve    # 批准大纲

# 写作
uv run python main.py write start        # 创建写作 checkpoint（--fresh 覆盖）
uv run python main.py write status       # 写作进度
uv run python main.py write resume all   # 续写全书（或 1、1.1、1.1.1 指定范围）
uv run python main.py write audit        # 出版审计诊断
uv run python main.py write export all   # 导出（markdown/word/pdf/all）

# 图表
uv run python main.py write figures build       # 生成图表资产
uv run python main.py write figures audit       # 审计图表覆盖率

# 引用标记
uv run python main.py write references audit    # 审计 [S]/[W] 标记
uv run python main.py write references clean    # 清理标记（--mode remove/footnote/endnote）
```

## Testing & Linting

```bash
uv run pytest                              # 全部测试
uv run pytest tests/test_state.py          # 单文件
uv run pytest tests/test_state.py::test_fn  # 单测试
uv run ruff check .                        # lint
uv run ruff format --check .               # 格式检查
uv run mypy core agents                    # 类型检查
```

## Architecture

### Two-Layer Structure

- **`core/`** — 基础设施：LLM 客户端、RAG 引擎、状态模型、配置、质量规则、输出生成
- **`agents/`** — 多 Agent 编排：每个 Agent（`BaseAgent` 子类）封装一个 LLM 驱动的角色

### Key Components

- **`core/workflow.py` — `BookProject`**：核心编排器，三阶段流水线（kb/outline/write）。写入操作使用文件锁（`_write_operation_lock`）防止并发冲突。
- **`core/state.py` — `BookState`**：Pydantic 模型，全书状态的唯一真相源。贯穿大纲、写作、审校、导出全流程。
- **`core/config_models.py` — `AppConfig`**：强类型配置（`extra="forbid"`），从 `config/*.yaml` 加载。配置拼写错误会直接报错。
- **`cli.py`**：Typer CLI，`kb`/`outline`/`write` 三个子命令组，`write` 下还有 `figures`/`references` 子组。
- **`core/llm_client.py` — `LLMClient`**：统一 LLM 调用，支持 chat/embed，带重试和超时。
- **`core/rag.py` — `RAGEngine`**：混合检索（dense + BM25 + RRF），可选 rerank 和 contextualize。

### Agent Pipeline

`agents/` 下每个文件对应一个角色：
- `planner` → `plan_reviewer` → `chapter_architect`：大纲阶段
- `research` → `writer` → `assembler`：写作阶段
- `fact_checker` + `citation_guard` + `style_guard` + `editor`：质量门（对抗式多视角复核，`_adversarial_vote`）
- `director`：全书终审
- `figure_designer`：图表资产生成

### Data Flow

```
config/*.yaml → AppConfig → BookState
                            ↓
                    .data/outlines/current.json → approved.json
                            ↓
                    .data/write/<thread-id>.json (checkpoint)
                            ↓
                    .data/manuscript/chapter-XX/section-id.md
                            ↓
                    output/ (book.md, book.docx, book.pdf)
```

### Concurrency Model

写作支持章节级并发（`writing.parallel_chapters`），每个章节在独立 `BookProject` 实例中顺序写完，通过 `_merge_chapter_state` 合回主线程 checkpoint。Worker checkpoint 存放在 `.data/write/workers/<thread-id>/chapter-XX.json`。

### Quality Gates

每个小节和章节都经过多轮质量审校：
- **小节级**：字数、标题、图表规格、禁用词（确定性检查）
- **章节级**：确定性门（字数/结构/原创性）→ LLM 四视角对抗门（事实/引用/风格/编辑）

## Config Directory

`config/` 下的 YAML 文件通过 `AppConfig` 加载，必须全部存在且拼写正确（`extra="forbid"`）：
- `book.yaml` — 书籍元数据
- `parts.yaml` — 篇章结构
- `style.yaml` — 写作风格与图表规范
- `llm.yaml` — LLM 和 Embedding 配置（含 API key，不入库）
- `references.yaml` — 参考资料源和检索策略
- `quality.yaml` — 出版质量门阈值
- `writing.yaml` — 写作流水线参数
- `output.yaml` — 输出路径和格式

## Environment

- Python 3.13，依赖管理用 `uv`
- `.env` 放 API key（`DEEPSEEK_API_KEY`、`OPENROUTER_API_KEY`），已 gitignore
- LLM 默认 DeepSeek，Embedding 默认 OpenRouter
