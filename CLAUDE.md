# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

book-builder 是一个纯手工写作 + 自动组装导出工具。不需要任何 Agent/LLM/RAG，作者在 `book/manuscript/` 下手工维护 Markdown 手稿，工具负责组装成层级化出版稿并导出 PDF。

所有资源统一放在 `book/` 目录下：配置 YAML、手稿、图表资产、封面、PDF 样式。

## Common Commands

```bash
uv run python main.py build              # 组装手稿 → 层级化 MD + book.md
uv run python main.py build --log-level DEBUG  # 详细日志
uv run python main.py build --skip-figures     # 跳过图表收集

uv run python main.py pdf                # 组装 + 导出 PDF
uv run python main.py pdf --skip-build   # 跳过组装，直接用已有 book.md
```

No tests, no linting — this is a pure writing tool.

## Architecture

```
book/*.yaml → src/book_builder/config.py (AppConfig)
                        ↓
book/manuscript/chapter-XX/chapter.md → src/book_builder/manuscript.py
                        ↓
book/figures/manifest.json → src/book_builder/figures.py (FigureAsset[])
book/figures/polished/     ↗
                        ↓
src/book_builder/output.py → output/{00-封面.md ... 08-附录.md, book.md, book_clean.md}
                           → generate_pdf_output() → pandoc → Chrome headless → book.pdf
```

### Key Components

- **`src/book_builder/config.py`** — 极简 Pydantic 配置模型（`extra="ignore"`）。从 `book/` 下 5 个 YAML 加载：`book/parts/style/author/output`。
- **`src/book_builder/manuscript.py`** — `load_manuscript(parts)` 遍历 parts 中的章节，优先读 `chapter.md`，不存在则从 `X.Y.Z.md` 节文件拼接。
- **`src/book_builder/figures.py`** — 扫描章节 markdown 中的 `book-figure` YAML 块，匹配 polished SVGs 或 manifest PNGs，复制到 `output/figures/`。`replace_book_figures_with_images()` 将代码块替换为 `<img>` 引用。
- **`src/book_builder/output.py`** — `generate_markdown_output()` 用 Jinja2 模板生成层级化 MD + 单文件 `book.md`。`generate_pdf_output()` 通过 pandoc + Chrome headless 生成 PDF。
- **`src/book_builder/cli.py`** — Typer CLI：`build` 和 `pdf` 两个命令。

### Data Flow

```
book/manuscript/chapter-01/chapter.md  (作者手工维护)
    ↓ build
output/05-基础篇 · 物联网平台底座/01-物联网概述：从连接到智能.md
output/book.md                           (单文件合集)
    ↓ pdf
output/book.pdf
```

## Resource Directory

`book/` 统一存放所有配置与资源：

- `book/book.yaml` — 书名/作者/ISBN
- `book/parts.yaml` — 篇章结构（只保留 `id`/`title`，agent 字段自动忽略）
- `book/style.yaml` — `illustrations` 图表渲染配置（marker/类型/调色板等）
- `book/author.yaml` — 作者简介 + 序言/导读内容
- `book/output.yaml` — 输出目录/pandoc 路径
- `book/manuscript/` — 14 章手稿 (chapter-01~14/chapter.md)
- `book/figures/` — 图表资产 manifest
- `book/figures/polished/` — 出版级 SVG 图表
- `book/cover.html` — PDF 封面

## Environment

- Python 3.13，依赖管理用 `uv`
- pandoc + Chrome/Edge 是 PDF 导出的系统依赖（非 Python 包）
- `.env` 不再需要（无 LLM API key）
