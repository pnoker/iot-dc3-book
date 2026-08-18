# iot-dc3-book

《从工业软件到 AI 智能体》在线书籍站点（https://book.dc3.site）——**手稿即终稿**：没有导出中间层，改完手稿跑一次构建，网站立即反映。中英双语（英文增量翻译中）。

## 用法

```bash
pnpm install        # Node 依赖
uv sync             # Python 依赖（pyyaml、jinja2）

pnpm web            # 手稿 → docs/（唯一转换入口，或 uv run python scripts/build_web.py）
pnpm dev            # 本地开发（web + vitepress dev，改手稿后重跑/热更）
pnpm build          # 生产构建（web + vitepress build + sitemap/feed/llms）
pnpm preview        # 预览 dist
```

## 内容结构

```
iot-dc3-book/
├── book/                      # 出版资源（真相源）
│   ├── WRITING_GUIDE.md       #   写作规范（唯一来源）
│   ├── config/                #   book/parts(-en)/style/output YAML
│   ├── manuscript/            #   中文终稿：chapter-XX/X.Y.md + preface/ + appendix.md
│   ├── manuscript-en/         #   英文终稿：镜像结构，翻多少生成多少（README 有约定与进度）
│   ├── figures/chapter-XX/    #   {fig-id}.html 图源 + {fig-id}.yaml 图注册表（spec + 双语 caption/labels）
│   ├── dividers/              #   章/篇扉页模板（web 内联渲染）
│   └── assets/                #   cover.html / cover.png / logo.svg
├── scripts/                   # 构建与工具
│   ├── build_web.py           #   手稿 → VitePress 站点（唯一转换器）
│   ├── fig_theme.py           #   SVG 主题化（明暗）+ 图注册表 + 色值审计
│   └── extract_figure_i18n.py #   图内英文标注翻译桩
├── docs/                      # VitePress 站点源（zh 根路径 + /en/ locale）
└── .github/workflows/         # Pages 部署（pnpm build → dist）
```

## 手稿与插图约定

- 每章一个 `chapter-XX/` 目录，每节一个 `X.Y.md` 文件（H2 节标题 + 节内 H3/H4），可选 `_intro.md` 章引言；
- 卷首与附录是普通手稿文件：`preface/{author,foreword,guide}.md`、`appendix.md`（中英同构）；
- 插图在手稿中只用语言无关锚点 `@[fig-XX-YY]`（独立一行）；图的规格、双语图注（`caption.zh/en`）与图内英文标注映射（`labels.en`）在 `book/figures/chapter-XX/{fig-id}.yaml` 注册表管理；
- 构建时锚点替换为内联 SVG：色值 → CSS 变量（明暗主题），英文页按 `labels.en` 替换图内文本；构建器会告警缺图源或英文页残留中文标注的图；
- 修改手稿前先读 `book/WRITING_GUIDE.md`；翻译约定见 `book/manuscript-en/README.md`。

## 系统依赖

- Python 3.11+（`uv` 管理）、Node 24 + pnpm
- `git-lfs`：首次检出后 `git lfs install && git lfs pull`
- Chrome/Edge + pdftoppm（可选）：仅手动重渲染封面 `book/assets/cover.png` 时需要
