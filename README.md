# book-builder

纯手工写稿 + 自动组装成书。从 `book/manuscript/` 下的 Markdown 手稿组装层级化出版稿，导出 PDF。

## 用法

```bash
# 组装手稿 → 层级化 MD + 单文件 book.md
book-builder build

# 组装 + 导出 PDF（需要 pandoc + Chrome/Edge）
book-builder pdf
```

## 目录结构

```
book-builder/
├── main.py               # 入口
├── src/book_builder/     # 组装导出包
│   ├── cli.py
│   ├── config.py         # 配置模型与加载
│   ├── manuscript.py     # 手稿文件系统读取
│   ├── figures.py        # book-figure 图表扫描与替换
│   ├── output.py         # Markdown 组装 + PDF 生成
│   ├── pdf_style.css     # PDF 样式
│   └── templates/        # Jinja2 模板
├── book/                 # 配置 + 手稿 + 图表
│   ├── *.yaml            # 5 个 YAML 配置
│   ├── cover.html        # PDF 封面
│   ├── manuscript/       # 14 章手稿 (chapter-01~14/chapter.md)
│   └── figures/          # 图表资产 (manifest + polished/)
└── output/               # 构建产物
```

## 系统依赖

- **Python 3.11+**
- **pandoc** — Markdown → HTML（PDF 导出需要）
- **Chrome/Edge** — HTML → PDF 渲染（可选，无则仅输出 Markdown）

## 手稿写作约定

- 每章一个 `book/manuscript/chapter-XX/` 目录，写 `chapter.md` 作为完整章内容
- 图表用 ` ```book-figure` YAML 块描述，build 时自动替换为实际图片
- `book/figures/polished/chapter-XX/` 下放出版级 SVG/PNG 图表
- `book/parts.yaml` 定义篇章结构，新增章节需同步更新
