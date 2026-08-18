# AGENTS.md

本仓库是**纯在线书籍站点**：手稿即终稿，无导出中间层。允许使用 Agent 辅助手稿写作、翻译、审校和维护，构建链路不依赖 Agent。

## 项目概览

网站是这本书的唯一产品形态。作者维护 `book/manuscript/`（中文终稿）与 `book/manuscript-en/`（英文终稿，镜像结构、增量翻译），`scripts/build_web.py` 把手稿一对一渲染成 VitePress 页面（`docs/`，中英两个 locale）——**改完手稿跑一次构建，网站立即反映，没有任何"组装/导出"环节**。

- 中文站：根路径；英文站：`/en/`（未翻译的章保持纯中文，侧栏为纯文本条目）。
- PDF/整书导出已取消：不存在 `output/`、`src/book_builder/`，也不要重新引入导出中间层。

所有出版资源统一放在 `book/` 目录下：配置、写作指南、双语手稿、插图源、图注册表、封面与扉页。

## 修改手稿前

修改手稿前必须阅读并遵循：

- `book/WRITING_GUIDE.md`：全书写作规范的唯一来源；
- `book/config/book.yaml`：书名、署名和站点元数据；
- `book/config/parts.yaml`：中文篇章结构的唯一来源；
- `book/config/parts-en.yaml`：英文篇章结构（章 id 与 parts.yaml 一一对应）；
- `book/config/style.yaml`：图表字段、类型和配色的唯一来源。

不要在本文件复制写作规范或图表 schema，避免产生多个权威来源。

## 工作约束

- 只修改任务直接涉及的手稿、图注册表或构建代码，不顺带重写其他章节；
- 修改章节标题、编号或顺序后，检查目录、导读和跨章节引用；
- 插图规格/双语图注只在图注册表（`book/figures/chapter-XX/{figure_id}.yaml`）里改，手稿只放 `@[fig-XX-YY]` 锚点；
- 修改 `book-figure` 视觉时遵守 `style.yaml`，其中 `legend` 选填；
- 需要生成或重绘架构、拓扑、分层、数据流等插图时，使用项目技能 `/book-architecture-diagram`，不要使用同名外部深色架构图技能；
- 版本、标准、API 和性能数据先查一手资料；
- 完成后运行 `uv run python scripts/build_web.py`（或 `pnpm build`），确认手稿渲染与图表扫描成功。

## 双语约定

- 英文手稿树 `book/manuscript-en/` 与中文树镜像：`chapter-XX/X.Y.md` 节文件 + 可选 `_intro.md`；卷首 `preface/*.md`、附录 `appendix.md` 同构；
- 翻译多少生成多少：缺章在英文侧栏显示为纯文本；卷首/附录缺文件则该页不生成；
- 插图锚点 `@[fig-XX-YY]` 语言无关，两棵树用同一锚点；图注/图内标注双语在图注册表管理；
- 图内英文标注用 `scripts/extract_figure_i18n.py` 生成桩再填译文，构建时会审计英文页仍含中文标注的图；
- 术语以中文版附录 A 术语表为准（物模型=thing model、位号值=point value 等）。

## 插图生产规范

本节规定插图的生产流程和质量要求；字段 schema、允许类型、画布尺寸、字体范围和配色值仍以 `book/config/style.yaml` 为唯一权威来源。通用绘图模板或外部 Skill 与本仓库风格冲突时，以 `style.yaml` 和本节为准。

### 源文件与命名

- `book/figures/chapter-XX/{figure_id}.html` 是插图的唯一可编辑源；同一目录的 `{figure_id}.yaml` 是图注册表（spec + `caption.zh/en` + `labels.en`），二者同名成对、一一对应；
- 手稿锚点 `@[fig-XX-YY]`、HTML 文件名、yaml 文件名和图内图号必须一一对应；
- 插图使用自包含 HTML + 内联 SVG，不引用远程字体、图片、脚本或其他网络资源；
- 每个 HTML 必须且只能包含一个 `data-figure-root`，并提供 SVG `title`、`desc` 和可访问性关联；
- 站点在构建时把 SVG 源内联进页面（色值替换为 CSS 变量，响应明暗主题；英文页按 `labels.en` 替换文本），不存在 PNG 导出链路。

### 视觉与版式

- 使用浅色技术出版风格和中文友好字体，禁止页码、装饰性网格、水印、工具栏和与内容无关的视觉元素；
- 画布逻辑宽度、高度区间、字号和颜色直接读取或遵守 `style.yaml`，不得另建配色体系；
- 顶部必须有以规范图号开头的图标题，底部必须有以同一图号开头的独立图注；图注说明结论，不机械复述标题；
- 信息层级依次为标题、核心结构、关键标注、补充说明和图注；主要内容应占据画布主体，避免大面积无意义留白；
- 同级模块保持等宽、等高、等距和统一描边；标题区与内容区边框粗细必须一致；
- 卡片、分组边界和安全域使用稳定的圆角与留白，不得相互压线、遮挡或出现"支棱出画布"的模块；
- 不能只依赖颜色表达语义，必要时同时使用短标签、线型或形状，保证灰度打印和缩放后仍可辨认；
- 图内英文标注要紧凑（SVG 文本框按中文宽度排布），填完译文后建议目视检查是否溢出。

### 连线与箭头

- 先确定数据流、控制流、调用关系或依赖关系，再绘制连线；每条线必须有明确语义，避免纯装饰连接；
- 连线优先走模块间空隙，禁止穿过卡片、文字、图标、图注和其他关键标注；交叉不可避免时应调整布局，而不是堆叠更多折线；
- 同类连线统一颜色、粗细、虚实和箭头尺寸，不同语义通过颜色与线型共同区分；
- 箭头大小按图的密度和主次关系选择，不要求所有图机械统一；主链路可使用较大箭头，密集架构图使用较小箭头；
- SVG 中先绘制连线、后绘制节点和标签，或使用不透明底色遮罩，防止连线透过卡片；连接标签最后绘制，确保不被边框覆盖；
- 避免重复竖线、悬空箭头、错误落点、回折过多、短线贴边和箭头压线；闭环链路应能一眼看出起点、方向和终点。

### 内容质量

- 绘图前先核对图注册表中的 `purpose`、`audience_takeaway`、`elements`、`relationships` 和 `caption`，描述不足时先修正文案再绘图；
- 一张图只表达一个核心认知，优先展示边界、主链路和关键职责，不把正文全部塞入图中；
- 模块名称使用短名词短语，解释性内容放在副标题、callout 或正文；协议名、产品名和缩写保持原文；
- 架构图应体现层次、边界和方向，流程图应体现顺序、分支和回路，对比图应保持左右或上下结构严格对齐；
- 涉及 AI 控制工业设备时，必须画出权限、策略、确认、审计或确定性执行边界，不得表现为模型无条件直连设备。

### 验收

1. 修改 HTML 源或注册表；
2. 运行 `uv run python scripts/build_web.py`，确认无"缺少 SVG 源/残留中文标注"告警；
3. `pnpm dev` 打开对应页面目视检查（明/暗主题各看一遍），重点检查文字溢出、中文截断、模块重叠、等距、描边、箭头、压线、留白、图号和图注；
4. 运行 `git diff --check`。

目视检查不能被构建成功替代。构建器只能证明资源可加载，不能判断图是否美观、清晰或存在视觉遮挡。

## 常用命令

```bash
# 手稿 → VitePress 站点（唯一构建入口）
uv run python scripts/build_web.py          # 或 pnpm web
pnpm build                                  # web + vitepress build + sitemap/feed/llms
pnpm dev                                    # web + vitepress dev（改手稿后自动反映）

# 图注册表英文标注桩（翻译图内标注用）
uv run python scripts/extract_figure_i18n.py fig-01-05          # 打印
uv run python scripts/extract_figure_i18n.py chapter-01 --write # 整章写入注册表

# 改 book/assets/cover.html 后手动重渲染封面静态图（og:image）
# （Chrome --print-to-pdf + pdftoppm，产物 book/assets/cover.png）
```

本仓库没有独立的测试或 lint 命令。修改后至少运行 `pnpm web`；改插图后用 `pnpm dev` 目视检查。

## 构建架构

```text
book/manuscript/（中文终稿）  book/manuscript-en/（英文终稿）
        │   @[fig-XX-YY] 锚点（语言无关）
        ▼
book/figures/chapter-XX/{fig-id}.html（图源）+ {fig-id}.yaml（注册表：spec + 双语 caption + labels）
        │   scripts/fig_theme.py（色值→CSS 变量 + labels.en 文本替换）
        ▼
scripts/build_web.py ──→ docs/（zh 根路径 + /en/ locale）+ sidebar(.en).ts + public 静态资源
        ▼
vitepress build ──→ docs/.vitepress/dist（GitHub Pages 部署）
```

关键模块：

- `scripts/build_web.py`：手稿→站点唯一转换器（章组装、锚点→内联 SVG、扉页内联、frontmatter、目录/侧栏、双语生成）；
- `scripts/fig_theme.py`：SVG 主题化（明暗变量）、图注册表加载、色值覆盖审计；
- `scripts/extract_figure_i18n.py`：图注册表 `labels.en` 桩生成/同步；
- `docs/.vitepress/`：`config.ts`（locales：zh 根 + en）、`seo.ts`（双语 hreflang/og/JSON-LD）、`sidebar.ts`/`sidebar.en.ts`（生成物）、theme 组件；
- `scripts/gen-og-image.mjs` / `enhance-sitemap.cjs` / `generate-feed.cjs` / `generate-llms-full.cjs`：构建后处理（og 图手动、其余在 `pnpm build` 内）。

## 资源目录

- `book/WRITING_GUIDE.md`：全书写作规范；
- `book/config/`：书籍、篇章（中/英）、样式和输出配置；
- `book/manuscript/`：中文终稿（14 章节文件 + `preface/` + `appendix.md`）；
- `book/manuscript-en/`：英文终稿（镜像结构，附 README 约定与进度表）；
- `book/figures/chapter-XX/`：`{figure_id}.html` 图源 + `{figure_id}.yaml` 图注册表；
- `book/dividers/`：章/篇扉页 HTML 模板（web 内联渲染）；
- `book/assets/`：`cover.html`（封面模板）、`cover.png`（og:image 静态产物）、`logo.svg`；
- `promotion/`：推广文案、Slides 源文件和导出图片；
- `docs/`：VitePress 源（生成内容页 + 手写 `index.md`、`en/index.md`、`en/copyright.md`、`figures.md`、`copyright.md`）。

## 环境依赖

- Python 3.11+，依赖由 `uv` 管理（pyyaml、jinja2）；
- `git-lfs`：管理 PNG 等二进制资产，首次检出后运行 `git lfs install && git lfs pull`；
- Node + pnpm：VitePress 站点构建；
- Chrome/Edge + pdftoppm（可选）：仅手动重渲染封面时需要。
