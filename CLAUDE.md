# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

book-builder 是一个纯手工写作 + 自动组装导出工具。构建工具本身不依赖 Agent/LLM/RAG；作者可手工维护或借助 Agent 辅助维护 `book/manuscript/` 下的 Markdown 手稿，工具负责组装成层级化出版稿并导出 PDF。

所有资源统一放在 `book/` 目录下：配置、写作指南、手稿、图表资产、封面、PDF 样式。

## Manuscript Guidelines

修改 `book/manuscript/` 前必须先阅读并遵循：

- `book/WRITING_GUIDE.md`：全书写作规范的唯一来源；
- `book/config/book.yaml`：书籍元数据；
- `book/config/parts.yaml`：篇章结构；
- `book/config/style.yaml`：图表规格与视觉参考。

不要在本文件重复维护写作规范。修改篇章结构后检查目录、导读和跨章节引用；修改 `book-figure` 后运行 build 验证。

## Common Commands

```bash
uv run book-builder build              # 组装手稿 → 层级化 MD + book.md
uv run book-builder build --log-level DEBUG  # 详细日志
uv run book-builder build --skip-figures     # 跳过图表收集

uv run book-builder pdf                # 组装 + 导出 PDF
uv run book-builder pdf --skip-build   # 跳过组装，直接用已有 book.md

uv run book-builder sample             # 生成样稿 PDF（只到第1章，提交编辑社）
uv run book-builder sample --until-chapter 3  # 样稿到第3章
```

No tests, no linting — this is a pure writing tool.

## Architecture

```
book/config/*.yaml → src/book_builder/config.py (AppConfig)
                        ↓
book/manuscript/chapter-XX/chapter.md → src/book_builder/manuscript.py
                        ↓
book/figures/chapter-XX/{figure_id}.png → src/book_builder/figures.py (FigureAsset[])
                        ↓
src/book_builder/markdown.py → output/{00-封面.md ... 08-附录.md, book.md, book_clean.md}
src/book_builder/pdf.py      → generate_pdf_output() → pandoc → Chrome headless → book.pdf
```

### Key Components

- **`src/book_builder/config.py`** — 极简 Pydantic 配置模型（`extra="ignore"`）。从 `book/config/` 下 5 个 YAML 加载：`book/parts/style/author/output`；校验书籍署名与作者简介姓名一致。
- **`src/book_builder/manuscript.py`** — `load_manuscript(parts)` 遍历 parts 中的章节，优先读 `chapter.md`，不存在或为空则从 `X.Y.Z.md` 节文件按编号排序拼接。
- **`src/book_builder/figures.py`** — 扫描章节 markdown 中的 `book-figure` YAML 块，按 `figure_id` 在 `book/figures/chapter-XX/` 找同名 PNG 匹配资产，复制到 `output/figures/`。未匹配的不阻断构建，原 `book-figure` 块保留。`replace_book_figures_with_images()` 将代码块替换为图片引用（层级文件用 `../` 前缀，book.md 用直接路径）。
- **`src/book_builder/markdown_assets.py`** — `book-figure` 代码块解析与 YAML payload 规范化，供 figures.py 复用。
- **`src/book_builder/markdown.py`** — `generate_markdown_output()` 用 Jinja2 模板组装层级化分章 MD + 单文件 `book.md` + 封面图（`cover.png`）。
- **`src/book_builder/pdf.py`** — `generate_pdf_output()` 通过 pandoc → Chrome headless 生成 PDF，封面单独渲染并用 pypdf 合并，中间文件自动清理；`generate_cover_image()` 把封面 HTML 渲染为 PNG。
- **`src/book_builder/log.py`** — 基于 rich 的统一日志，控制台 + 轮转文件（`logs/book-builder.log`）。
- **`src/book_builder/cli.py`** — Typer CLI：`build`、`pdf`、`sample` 三个命令，入口 `book_builder.cli:main`。

### Data Flow

```
book/manuscript/chapter-XX/chapter.md  (作者手工维护)
    ↓ build
output/00-封面.md … 08-附录.md       (层级化分章 MD)
output/05-篇名/01-章名.md
output/万物智联.md   (单文件合集，含图引用)
output/cover.png      (封面图)
output/figures/       (图表 PNG)
    ↓ pdf
output/万物智联.pdf  (中间文件自动清理)
```

## Resource Directory

`book/` 统一存放所有配置与资源：

- `book/WRITING_GUIDE.md` — 人工作者与 Agent 共用的全书写作规范
- `book/config/` — 5 个 YAML 配置（`book`/`parts`/`style`/`author`/`output`）
  - `parts.yaml` 篇章结构（篇 `name`/`prefix`，章 `id`/`title`）
  - `style.yaml` 图表规格与视觉参考（机器校验字段 + 外部制图配色）
- `book/assets/` — 静态资源（`cover.html` 封面、`logo.svg` 封面 logo）
- `book/manuscript/` — 14 章手稿（chapter-01~14/chapter.md，可拆分为 `X.Y.Z.md` 节文件）
- `book/figures/chapter-XX/` — 图表资产（`{figure_id}.html`/`.svg`/`.png`，文件名与手稿 `figure_id` 一致；命名统一规则）

## Environment

- Python 3.13（开发版本，兼容 3.11+），依赖管理用 `uv`
- Python 依赖：`pyyaml`、`typer`、`jinja2`、`pydantic`、`rich`、`pypdf`
- 系统依赖（非 Python 包）：
  - `pandoc` — Markdown → HTML（PDF 导出必需）
  - Chrome/Edge — HTML → PDF 渲染（PDF 导出必需，无则仅输出 Markdown）
  - `pdftoppm`（可选）— 封面 HTML → PNG，缺失时回退 `sips`（macOS）或 Chrome 截图
- `.env` 不再需要（无 LLM API key）
