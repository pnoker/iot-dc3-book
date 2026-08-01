# book-builder

纯手工写稿 + 自动组装成书。从 `book/manuscript/` 下的 Markdown 手稿组装层级化出版稿，导出 PDF。构建工具不依赖 Agent/LLM/RAG，也支持按统一写作指南使用 Agent 辅助写作。

## 用法

```bash
# 组装手稿 → 层级化 MD + 单文件 book.md
uv run book-builder build

# 组装 + 导出 PDF（需要 pandoc + Chrome/Edge）
uv run book-builder pdf
uv run book-builder pdf --skip-build   # 跳过组装，直接用已有 book.md

# 生成样稿 PDF（只到第1章，提交编辑社）
uv run book-builder sample
uv run book-builder sample --until-chapter 3   # 样稿到第3章
```

## 目录结构

```
book-builder/
├── pyproject.toml       # 入口 book_builder.cli:main
├── src/book_builder/    # 组装导出包
│   ├── cli.py            # Typer CLI（build / pdf）
│   ├── config.py         # Pydantic 配置模型与加载
│   ├── manuscript.py     # 手稿文件系统读取
│   ├── figures.py        # book-figure 图表扫描与替换
│   ├── markdown_assets.py# book-figure 块解析
│   ├── markdown.py       # Markdown 组装
│   ├── pdf.py            # PDF 生成 + 封面渲染
│   ├── log.py            # rich 统一日志
│   ├── pdf_style.css     # PDF 样式
│   └── templates/        # Jinja2 模板
├── book/                 # 配置 + 写作指南 + 手稿 + 图表
│   ├── WRITING_GUIDE.md  # 人工作者与 Agent 共用的写作规范
│   ├── config/           # 5 个 YAML 配置
│   ├── assets/           # cover.html + logo.svg
│   ├── manuscript/       # 14 章手稿 (chapter-01~14/chapter.md)
│   ├── figures/          # 制图源 HTML (chapter-XX/{figure_id}.html)
│   └── assets/           # 静态资源 (images/ 渲染图PNG, cover.html, logo.svg)
└── output/               # 层级 MD + 书名.md/.pdf/—样稿.pdf + cover.png + figures/
```

## 系统依赖

- **Python 3.13**（兼容 3.11+），依赖管理用 `uv`
- **pandoc** — Markdown → HTML（PDF 导出需要）
- **Chrome/Edge** — HTML → PDF 渲染（PDF 导出需要，无则仅输出 Markdown）
- **pdftoppm**（可选）— 封面 PNG 生成，缺失时回退 `sips` 或 Chrome 截图

## 手稿写作约定

- 修改手稿前先阅读 `book/WRITING_GUIDE.md`；它是人工写作和 Agent 辅助写作共用的规范
- 每章一个 `book/manuscript/chapter-XX/` 目录，写 `chapter.md` 作为完整章内容；不存在时可拆分为 `X.Y.Z.md` 节文件，工具按编号排序拼接
- 图表用 ` ```book-figure` YAML 块描述规格，build 时自动替换为 PNG 图片；字段、类型和配色以 `book/config/style.yaml` 为准，`legend` 选填
- 图表按 `figure_id` 在 `book/assets/images/chapter-XX/` 找同名 PNG（`{figure_id}.png`）；未匹配的原块保留
- `book/config/parts.yaml` 定义篇章结构（篇 `name`/`prefix`，章 `id`/`title`），新增章节需同步更新
- `book/config/book.yaml` 是封面、Pandoc metadata 和输出文件名的书籍元数据来源
- CLI 未传 `--output` 时使用 `book/config/output.yaml` 的 `dir`，显式参数优先
