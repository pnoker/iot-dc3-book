---
name: book-architecture-diagram
description: Create or redraw publication-grade illustrations for this IoT DC3 book as self-contained light-themed HTML+SVG sources and export matching PNG assets. Use for architecture, topology, data-flow, layered, sequence, flowchart, lifecycle, matrix, pyramid, timeline, and framework figures under book/figures.
---

# IoT DC3 Book Architecture Diagram

为《从工业软件到 AI 智能体》创建或重绘出版级技术插图。此技能只服务当前仓库，产物必须适配书稿、PDF 和网站，不得套用通用深色架构图模板。

## 权威来源

开始前依次阅读：

1. `AGENTS.md` 的“插图生产规范”；
2. `book/config/style.yaml` 的 `illustrations` 配置；
3. `book/WRITING_GUIDE.md` 的“图表”章节；
4. 目标手稿中的完整 `book-figure` 块；
5. 同章已被用户认可的插图，例如 `book/figures/chapter-01/fig-01-04.html`。

冲突时优先级为：用户当前要求 > `style.yaml` > `AGENTS.md` > `WRITING_GUIDE.md` > 本技能模板。不要把本技能写死的示例值当成新的权威配置。

## 任务流程

### 1. 先确认图意

从 `book-figure` 中提取并核对：

- `id`、`type`、`title`、`purpose`；
- `audience_takeaway`；
- `elements`、`relationships`；
- `caption`、`render_notes`。

如果描述不能回答“这张图要让读者一眼理解什么”“主链路从哪里到哪里”“哪些边界必须出现”，先改进图的描述，再绘制。不要用布局掩盖内容设计不足。

### 2. 选择信息结构

- `architecture` / `topology` / `dataflow`：优先表达系统边界、分组和主链路；
- `layered` / `pyramid`：同级模块严格对齐，层次方向明确；
- `sequence`：参与者横向排列，时间从上到下；
- `flowchart` / `lifecycle`：步骤顺序、决策分支和回路清楚；
- `matrix`：比较维度稳定，单元格不塞长段文字；
- `timeline`：阶段从左到右，时间、驱动力和变化量分层展示；
- `framework`：突出组成、约束和相互关系，避免画成无方向的卡片集合。

一张图只承担一个核心认知。信息过多时删减次要细节或拆图，不缩小字号硬塞。

### 3. 计算布局后再写 SVG

先确定以下几何参数：

- 1200px 逻辑宽度和适合内容密度的高度；
- 主体有效区域和四周留白；
- 同级卡片数量、宽度、高度、间距；
- 连线通道、标签位置、图例和图注区域；
- 需要避开的文字、边界和安全域。

同级模块必须等宽、等高、等距；确需强调的主模块可以更宽，但必须形成有意图的比例，而不是随机尺寸。

## 设计系统

### 画布与字体

- 逻辑宽度固定为 1200px，PNG 由构建器统一导出为 2400px；
- 高度按 `style.yaml` 的紧凑、标准、复杂区间选择，不为凑版面制造空白；
- 使用 `PingFang SC`、`Microsoft YaHei`、`Noto Sans SC`、Arial 的离线字体栈；
- 标题、组件、副标签、注释和图注字号遵守 `style.yaml`；
- 禁止负 `letter-spacing`、页码、水印、装饰性网格和无意义阴影。

### 颜色语义

颜色必须来自 `style.yaml`：

- 蓝色：核心平台、主要数据链路；
- 青绿：设备、边缘、接入或控制回路；
- 紫色：数据、存储或独立业务域；
- 橙色：AI、智能、关键增量能力；
- 红色：风险、安全边界或高风险受控动作；
- 琥珀色：外部系统、提醒或治理说明；
- 灰色：普通边界、辅助线和次要依赖。

不要只用颜色区分语义；同时使用标题、线型、边框或短标签，保证灰度打印可读。

### 标题与图注

- HTML `<title>`、SVG `<title>`、顶部可见标题、底部可见图注必须使用同一规范图号；
- SVG 必须包含非空 `<desc>`，并由 `aria-labelledby` 同时关联 `<title>` 与 `<desc>`；
- 顶部标题说明“是什么”，副标题说明“核心结论”；
- 底部图注必须独立说明读者应获得的结论，不能只重复标题；
- 不显示页码、制图工具标识、类型徽章或导出按钮。

### 卡片与边界

- 卡片使用浅色填充、清晰描边和稳定圆角；
- 同一组卡片描边粗细统一，标题区填充不得覆盖外框导致上细下粗；
- 区域边界与内部组件至少留出 20px 间距；
- 图例放在所有边界框之外，不遮挡主体；
- 模块不得触边、越界、互相覆盖或与图注重叠。

### 连线与箭头

- 先绘制连线，再绘制不透明节点，最后绘制连接标签；
- 连线从节点边缘出发并落到目标节点边缘，不在卡片内部悬空；
- 连线优先水平、垂直或单次转折，避免多次回折和无意义交叉；
- 标签放在线路空隙中，并用不透明浅色底防止边框或线条穿字；
- 同类连线统一颜色、粗细、虚实和箭头形状；
- 箭头大小服从信息密度：主链路可以大，密集图要小；
- 闭环必须能明确识别起点、方向、受控边界和终点；
- 禁止重复竖线、重影箭头、箭头压线、命令回执压住连线或线条穿过文字。

## 输出要求

插图源必须是 `book/figures/chapter-XX/{figure_id}.html`：

- 单一、自包含 HTML；
- 内联 CSS 和内联 SVG；
- 不引用网络字体、远程图片、CDN 或脚本；
- 不包含 JavaScript、工具栏或交互导出逻辑；
- 页面中必须且只能有一个 `data-figure-root`；
- 根节点实际尺寸为 1200px × 内容高度；
- PNG 只通过 `book-builder figures` 从源 HTML 导出，不直接修改 PNG。

以 `resources/template.html` 为结构起点，但必须根据图意重新计算布局。模板中的三卡片示例不是固定架构，也不能原样复制到所有图。

## 验收流程

完成后必须依次执行：

```bash
uv run book-builder figures --figure-id <figure_id>
uv run python -c 'from book_builder.figure_audit import audit_figure_html; issues = audit_figure_html("book/figures", figure_id="<figure_id>"); print(f"issues={len(issues)}"); [print(f"{issue.source}: {issue.reason}") for issue in issues]'
git diff --check
uv run book-builder build
```

然后打开导出的 PNG 目视检查：

- 图号、标题和图注是否一致；
- 中文是否被截断；
- 模块是否等距、对齐、描边一致；
- 箭头方向、大小和落点是否合理；
- 是否存在压线、遮挡、重叠、重复连线和无意义留白；
- 缩小查看时主链路是否仍然清楚。

构建成功不代表视觉验收成功。发现视觉问题必须回到 HTML 源修正并重新导出。
