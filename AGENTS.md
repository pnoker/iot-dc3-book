# AGENTS.md

本仓库的构建工具不依赖 Agent，但允许使用 Agent 辅助手稿写作、审校和维护。

## 项目概览

`book-builder` 是一个“手工写作 + 自动组装导出”工具。作者维护 `book/manuscript/` 下的 Markdown 手稿，构建工具负责加载配置、组装章节、收集插图，并导出 Markdown 和 PDF。

所有出版资源统一放在 `book/` 目录下，包括配置、写作指南、手稿、插图源、渲染图片、封面和 PDF 样式。

## 修改手稿前

修改 `book/manuscript/` 前必须阅读并遵循：

- `book/WRITING_GUIDE.md`：全书写作规范的唯一来源；
- `book/config/book.yaml`：书名、署名和出版元数据；
- `book/config/parts.yaml`：篇章结构的唯一来源；
- `book/config/style.yaml`：图表字段、类型和配色的唯一来源。

不要在本文件复制写作规范或图表 schema，避免产生多个权威来源。

## 工作约束

- 只修改任务直接涉及的手稿、配置或构建代码，不顺带重写其他章节；
- 修改章节标题、编号或顺序后，检查目录、导读和跨章节引用；
- 修改 `book-figure` 时遵守 `style.yaml`，其中 `legend` 选填；
- 需要生成或重绘架构、拓扑、分层、数据流等插图时，使用项目技能 `/book-architecture-diagram`，不要使用同名外部深色架构图技能；
- 版本、标准、API 和性能数据先查一手资料；
- 完成后运行 `uv run book-builder build`，确认配置加载、手稿组装和图表扫描成功。

## 插图生产规范

本节规定插图的生产流程和质量要求；字段 schema、允许类型、画布尺寸、字体范围和配色值仍以 `book/config/style.yaml` 为唯一权威来源。通用绘图模板或外部 Skill 与本仓库风格冲突时，以 `style.yaml` 和本节为准。

### 源文件与命名

- `book/figures/chapter-XX/{figure_id}.html` 是插图的唯一可编辑源，PNG 不得脱离源文件单独修图；
- `book/assets/images/chapter-XX/{figure_id}.png` 必须由同名 HTML 导出，手稿 `book-figure.id`、HTML 文件名、PNG 文件名和图内图号必须一一对应；
- 插图使用自包含 HTML + 内联 SVG，不引用远程字体、图片、脚本或其他网络资源；
- 每个 HTML 必须且只能包含一个 `data-figure-root`，并提供 SVG `title`、`desc` 和可访问性关联；
- 只修改单张图时优先按 `--figure-id` 定向导出，避免全量导出产生无关 PNG 差异。

### 视觉与版式

- 使用浅色技术出版风格和中文友好字体，禁止页码、装饰性网格、水印、工具栏和与内容无关的视觉元素；
- 画布逻辑宽度、导出宽度、高度区间、字号和颜色直接读取或遵守 `style.yaml`，不得另建配色体系；
- 顶部必须有以规范图号开头的图标题，底部必须有以同一图号开头的独立图注；图注说明结论，不机械复述标题；
- 信息层级依次为标题、核心结构、关键标注、补充说明和图注；主要内容应占据画布主体，避免大面积无意义留白；
- 同级模块保持等宽、等高、等距和统一描边；标题区与内容区边框粗细必须一致；
- 卡片、分组边界和安全域使用稳定的圆角与留白，不得相互压线、遮挡或出现“支棱出画布”的模块；
- 不能只依赖颜色表达语义，必要时同时使用短标签、线型或形状，保证灰度打印和缩放后仍可辨认。

### 连线与箭头

- 先确定数据流、控制流、调用关系或依赖关系，再绘制连线；每条线必须有明确语义，避免纯装饰连接；
- 连线优先走模块间空隙，禁止穿过卡片、文字、图标、图注和其他关键标注；交叉不可避免时应调整布局，而不是堆叠更多折线；
- 同类连线统一颜色、粗细、虚实和箭头尺寸，不同语义通过颜色与线型共同区分；
- 箭头大小按图的密度和主次关系选择，不要求所有图机械统一；主链路可使用较大箭头，密集架构图使用较小箭头；
- SVG 中先绘制连线、后绘制节点和标签，或使用不透明底色遮罩，防止连线透过卡片；连接标签最后绘制，确保不被边框覆盖；
- 避免重复竖线、悬空箭头、错误落点、回折过多、短线贴边和箭头压线；闭环链路应能一眼看出起点、方向和终点。

### 内容质量

- 绘图前先核对手稿中的 `purpose`、`audience_takeaway`、`elements`、`relationships` 和 `caption`，描述不足时先修正文案再绘图；
- 一张图只表达一个核心认知，优先展示边界、主链路和关键职责，不把正文全部塞入图中；
- 模块名称使用短名词短语，解释性内容放在副标题、callout 或正文；协议名、产品名和缩写保持原文；
- 架构图应体现层次、边界和方向，流程图应体现顺序、分支和回路，对比图应保持左右或上下结构严格对齐；
- 涉及 AI 控制工业设备时，必须画出权限、策略、确认、审计或确定性执行边界，不得表现为模型无条件直连设备。

### 导出与验收

1. 修改 HTML 源文件；
2. 定向导出目标 PNG；
3. 打开导出的 PNG 进行目视检查，重点检查中文截断、模块重叠、等距、描边、箭头、压线、留白、图号和图注；
4. 运行图审计，确认编号、图注和自包含规则通过；
5. 运行 `git diff --check`；
6. 运行 `uv run book-builder build`，确认全书配置、手稿和图表扫描成功。

目视检查不能被构建成功替代。构建器只能证明资源可加载，不能判断图是否美观、清晰或存在视觉遮挡。

## 常用命令

```bash
uv run book-builder build
uv run book-builder build --log-level DEBUG
uv run book-builder build --skip-figures

uv run book-builder figures
uv run book-builder figures --chapter 1
uv run book-builder figures --figure-id fig-01-01

uv run python -c 'from book_builder.figure_audit import audit_figure_html; issues = audit_figure_html("book/figures"); print(f"issues={len(issues)}"); [print(f"{issue.source}: {issue.reason}") for issue in issues]'

uv run book-builder pdf
uv run book-builder pdf --skip-build

uv run book-builder sample
uv run book-builder sample --until-chapter 3
```

本仓库没有独立的测试或 lint 命令。修改后至少运行 `uv run book-builder build`；修改 HTML 插图后先运行相应的 `figures` 命令重新导出 PNG。

## 构建架构

```text
book/config/*.yaml → src/book_builder/config.py
                         ↓
book/manuscript/chapter-XX/X.Y.md → src/book_builder/manuscript.py
                         ↓
book/assets/images/chapter-XX/{figure_id}.png → src/book_builder/figures.py
                         ↓
src/book_builder/markdown.py → output/*.md + output/cover.png
src/book_builder/pdf.py      → pandoc + Chrome → output/*.pdf
```

关键模块：

- `src/book_builder/config.py`：加载 `book/config/` 下的 YAML，并构造应用配置；
- `src/book_builder/manuscript.py`：优先读取各章 `X.Y.md` 节文件（每个二级标题一个文件，按文件名排序拼接，恢复 H1 章 + H2 节 + 节内 H3/H4 结构），缺失时降级读取整章 `chapter.md`；
- `src/book_builder/figures.py`：扫描 `book-figure` 块，匹配并收集同名 PNG；
- `src/book_builder/figure_renderer.py`：将 `book/figures/` 下的 HTML 插图导出为 PNG；
- `src/book_builder/figure_audit.py`：检查 HTML 插图的图号、图注和出版规范；
- `src/book_builder/markdown.py`：生成分章 Markdown、全书 Markdown 和封面图；
- `src/book_builder/pdf.py`：通过 Pandoc 和 Chrome 生成 PDF；
- `src/book_builder/cli.py`：提供 `build`、`figures`、`pdf` 和 `sample` 等命令。

## 资源目录

- `book/WRITING_GUIDE.md`：全书写作规范；
- `book/config/`：书籍、作者、篇章、样式和输出配置；
- `book/manuscript/`：14 章手稿；
- `book/figures/chapter-XX/`：HTML/SVG 插图源，文件名为 `{figure_id}.html`；
- `book/assets/images/chapter-XX/`：由插图源导出的 PNG，文件名为 `{figure_id}.png`；
- `promotion/`：推广文案、Slides 源文件和导出图片；
- `output/`：构建产物，不作为手稿源编辑。

## 环境依赖

- Python 3.11+，依赖由 `uv` 管理；
- `git-lfs`：管理 PNG、PDF、JPG 等二进制资产，首次检出后运行 `git lfs install && git lfs pull`；
- Pandoc：Markdown 转 HTML/PDF；
- Chrome 或 Edge：HTML 插图和 PDF 渲染；
- `pdftoppm`：可选，用于封面转图，缺失时使用平台回退方案。
