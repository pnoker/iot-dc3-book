# book-builder

纯手工写稿 + 自动组装成书。从 `book/manuscript/` 下的 Markdown 手稿组装层级化出版稿，导出 PDF。不需要任何 Agent/LLM/RAG。

## 用法

```bash
# 组装手稿 → 层级化 MD + 单文件 book.md
uv run book-builder build

# 组装 + 导出 PDF（需要 pandoc + Chrome/Edge）
uv run book-builder pdf
uv run book-builder pdf --skip-build   # 跳过组装，直接用已有 book.md
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
├── book/                 # 配置 + 手稿 + 图表
│   ├── config/           # 5 个 YAML 配置
│   ├── assets/           # cover.html + logo.svg
│   ├── manuscript/       # 14 章手稿 (chapter-01~14/chapter.md)
│   └── figures/          # 图表资产 (chapter-XX/{figure_id}.{html,svg,png})
└── output/               # 层级 MD + book.md + book.pdf + cover.png + figures/
```

## 系统依赖

- **Python 3.13**（兼容 3.11+），依赖管理用 `uv`
- **pandoc** — Markdown → HTML（PDF 导出需要）
- **Chrome/Edge** — HTML → PDF 渲染（PDF 导出需要，无则仅输出 Markdown）
- **pdftoppm**（可选）— 封面 PNG 生成，缺失时回退 `sips` 或 Chrome 截图

## 手稿写作约定

- 每章一个 `book/manuscript/chapter-XX/` 目录，写 `chapter.md` 作为完整章内容；不存在时可拆分为 `X.Y.Z.md` 节文件，工具按编号排序拼接
- 图表用 ` ```book-figure` YAML 块描述规格，build 时自动替换为 PNG 图片
- 图表按 `figure_id` 在 `book/figures/chapter-XX/` 找同名 PNG（`{figure_id}.png`）；未匹配的原块保留
- `book/config/parts.yaml` 定义篇章结构（只读 `id`/`title`），新增章节需同步更新
