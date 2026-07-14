---
name: architecture-diagram
description: Create polished light-themed architecture diagrams as self-contained HTML+SVG files, tuned for print (books, PDF, Word). Use when the user asks for system, infrastructure, cloud, data-flow, layered, or topology diagrams for a printed publication.
---

# Architecture Diagram Skill（浅色·出版印刷版）

Create professional technical architecture diagrams as **self-contained HTML files** with inline SVG graphics and CSS styling. This is the project-local, **light-theme** variant tuned for print (books, PDF, Word export) — a white background keeps ink usage low and text legible on paper.

> 本文件是 book-writer 项目内置技能。图表生成管线会读取本文件的「设计系统」章节，作为出版级图表 prompt 的骨架。改这里 → 生成的图跟着变。

## Design System

### Color Palette（浅色语义配色）

背景为浅色，节点用**浅色半透明填充 + 饱和描边 + 深色文字**，保证印刷清晰。

| Component Type | Fill | Stroke | Text |
|---------------|------|--------|------|
| 核心平台 / 主链路 (primary) | `#EFF6FF` | `#2563EB` (blue-600) | `#0F172A` |
| 设备 / 边缘 / 接入 (edge) | `#ECFDF5` | `#0F766E` (teal-700) | `#0F172A` |
| 数据 / 存储 (data) | `#F5F3FF` | `#7C3AED` (violet-600) | `#0F172A` |
| 云 / 外部服务 (cloud) | `#FFFBEB` | `#D97706` (amber-600) | `#0F172A` |
| 安全 / 风险 (security) | `#FEF2F2` | `#DC2626` (red-600) | `#0F172A` |
| AI / 智能 (ai) | `#FFF7ED` | `#F97316` (orange-500) | `#0F172A` |
| 外部 / 通用 (external) | `#F8FAFC` | `#94A3B8` (slate-400) | `#0F172A` |

保持全书统一视觉语义：**蓝=核心平台，青绿=边缘/接入，紫=数据，橙=AI/智能，红=安全/风险，琥珀=云/外部，灰=外部依赖**。

### Typography（中文印刷字体）

使用系统无衬线中文字体栈（不依赖联网字体，保证离线渲染与印刷一致）：

```css
font-family: 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', Arial, sans-serif;
```

Font sizes: 标题 22–28px，组件名 13–15px，副标签 10–12px，注释 9–10px，图例 10–12px。中文字号不要过小，PNG 供 Word 印刷，文字不得重叠或糊成一团。

### Visual Elements

**Background:** `#F8FAFC` (slate-50) 浅色底，配极淡网格：

```svg
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#E2E8F0" stroke-width="0.5"/>
</pattern>
```

**Component boxes:** 圆角矩形 (`rx="10"`)，1.5px 描边，浅色填充，可选极淡投影。

**Region boundaries（职责/系统边界）:** 虚线描边 (`stroke-dasharray="8,4"`)，`rx="14"`，用琥珀或灰描边，透明填充；边界名称放左上角。

**Arrows:** 用 SVG marker 画箭头：

```svg
<marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
  <polygon points="0 0, 10 3.5, 0 7" fill="#64748B" />
</marker>
```

**Arrow z-order:** 连线在背景网格之后、组件盒子之前绘制，让箭头落在盒子背后。若盒子是半透明填充导致箭头透出，可在盒子位置先画一个不透明白色底 rect 再叠样式 rect。

**语义连线颜色:** 数据/主链路=蓝 `#2563EB`，控制/反向=青绿 `#0F766E`，事件/异步=虚线，安全流=红虚线 `#DC2626`。

### Spacing Rules

**CRITICAL:** 纵向堆叠组件要留够间距，避免重叠：

- 标准组件高度 60–80px；较大组件 100–140px。
- 组件间最小纵向间隙 40px。
- 内联连接元素（如消息总线）放在间隙中央，不与组件重叠。

### Legend Placement

**CRITICAL:** 图例放在**所有边界框之外**（区域边界、集群边界之下至少 20px），必要时扩大 viewBox 高度容纳图例。图例不遮挡主体。

### Layout Structure

1. **Header** — 图名（中文「图X-Y 标题」）+ 一句副标题说明核心结论
2. **Main SVG diagram** — 放在浅色圆角卡片容器内
3. **Info cards（可选）** — 图下方 2–3 张要点卡，承载 callouts / 关键说明
4. **Caption/Footer** — 出版级图注

### Layout 类型语义

- `architecture`/`topology`/`dataflow`：突出分组、边界与主链路
- `sequence`：突出参与者与时序（顶部参与者，消息向下）
- `flowchart`/`lifecycle`：突出步骤，决策用菱形，关键路径高亮
- `layered`/`pyramid`：突出层级职责与上下游关系（自下而上或自上而下）
- `matrix`：突出比较维度
- `timeline`：突出阶段（从左到右）

### Component Box Pattern

```svg
<rect x="X" y="Y" width="W" height="H" rx="10" fill="#EFF6FF" stroke="#2563EB" stroke-width="1.5"/>
<text x="CENTER_X" y="Y+26" fill="#0F172A" font-size="14" font-weight="600" text-anchor="middle">组件名</text>
<text x="CENTER_X" y="Y+44" fill="#475569" font-size="11" text-anchor="middle">副标签</text>
```

## Output（硬性要求）

产出**单一 self-contained `.html` 文件**：

- 内联 CSS（不依赖外部样式表、不联网加载字体）
- 内联 SVG（不引用外部图片）
- **不需要 JavaScript**（无导出工具栏、无 CDN 脚本）—— PNG 由渲染管线用 headless 浏览器截图生成，HTML 自身保持纯静态
- 浅色背景，中文标签短小，解释性文字放 callouts/信息卡，禁止 `节点1/节点2/最右侧/container/service/user` 等占位词
- 每张图只表达一个主结论，主链路高亮，边界/层级/时序/决策关系一眼可读

文件在任意现代浏览器直接打开即可正确渲染。
