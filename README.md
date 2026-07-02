# mi-book-writer

基于 LangGraph 的专业多 Agent 书籍写作系统，面向长篇技术书的规划、检索、写作、事实核查、风格校验、审校和输出。

## Agent 流程

```text
init → indexing → planning → plan_review
  → research → write → fact_check → style_check → editor_review → advance_chapter
  → final_review → output
```

核心质量门：

- `PlannerAgent`：全书大纲与伏笔规划。
- `ResearchAgent`：按章节生成检索查询并召回参考资料。
- `WriterAgent`：生成或修订章节正文。
- `FactCheckerAgent`：依据参考资料核查关键技术事实。
- `StyleGuardAgent`：校验标题层级、术语、禁用词和章节结构。
- `EditorAgent`：审校逻辑连贯性、伏笔、完整度和一致性。
- `DirectorAgent`：全书终审报告。

## 代码结构

```text
agents/              # 各写书 Agent 的提示词与调用封装
core/                # 状态、配置、LLM、RAG、输出等基础能力
graph/               # LangGraph 编排、路由和节点实现
config/              # 书籍、章节、风格、模型和输出配置
tests/               # 状态、节点、CLI、RAG、LLM 等回归测试
cli.py               # CLI 参数解析与命令分发
main.py              # 最小入口，兼容 book-writer 脚本
```

`graph/` 节点已按职责拆分：

- `node_lifecycle.py`：初始化、索引、规划、推进章节。
- `node_chapter.py`：检索、写作、修订。
- `node_quality.py`：事实核查、风格校验、审校、修订控制。
- `node_final.py`：终审和输出。

`core/` 的 RAG 能力已拆分：

- `rag_pdf.py`：PDF 文本提取。
- `rag_chunking.py`：文本分块。
- `rag_manifest.py`：索引输入签名与过期判断。
- `rag.py`：RAGEngine 编排 ChromaDB 与检索。

## 环境变量

不要把 API Key 写入配置文件。运行前设置：

```bash
export DEEPSEEK_API_KEY="..."
export OPENROUTER_API_KEY="..."
```

## 常用命令

```bash
# 默认运行；若同 thread-id 有未完成 checkpoint，会自动续跑
uv run python main.py run

# 兼容旧用法；等同于从 checkpoint 继续
uv run python main.py --resume
uv run python main.py resume

# 查看当前 checkpoint、下一节点、当前章节和 RAG 健康状态
uv run python main.py status

# 使用新 thread-id 开始一个独立任务
uv run python main.py --thread-id book-2 run

# 清空当前 thread-id 后从头重跑
uv run python main.py run --fresh

# 显式删除某个 thread-id 的 checkpoint
uv run python main.py reset --yes
```

## 局部修复章节

输出目录不是源数据。需要修某章时，应把人工修改回写到 checkpoint，再重新生成输出：

```bash
uv run python main.py patch-chapter --chapter-id 7 --file ./drafts/chapter-07.md --regenerate-output
```

需要让 LLM 按反馈局部修订某章时：

```bash
uv run python main.py revise-chapter --chapter-id 7 --feedback-file ./feedback/chapter-07.txt --regenerate-output
```

只根据当前 checkpoint 重新生成输出：

```bash
uv run python main.py regenerate-output
```

导出 checkpoint 供人工审阅或备份：

```bash
uv run python main.py export-state --file ./state/book-1.json
```

## 验证

```bash
uv run ruff check .
uv run pytest
uv run mypy --python-version 3.14 core agents graph main.py
```
