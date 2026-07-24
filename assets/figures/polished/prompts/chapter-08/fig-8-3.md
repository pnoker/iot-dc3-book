请按 architecture-diagram 技能的浅色出版印刷风格，重绘下面这张书籍插图。

硬性要求：
1. 输出 self-contained HTML，主体为 inline SVG；同时导出同名 SVG 与 PNG。
2. 使用 1800×900 白色画布、极淡网格、浅色填充、饱和描边、深色文字、圆角卡片和清晰箭头，图例置于主体边界外。
3. 节点短标签优先，解释写入 callouts；禁止“节点1/节点2/container/service/user”等占位词。
4. 每张图只表达一个主结论，主链路高亮，边界、层级、时序或决策关系必须一眼可读。
5. 中文字体使用系统无衬线字体栈；PNG 需适合 Word 印刷，文字不得重叠或过小。
6. 保持全书统一视觉语义：蓝=核心平台，青绿=边缘/接入，橙=AI/智能，紫=数据，红=安全/风险，灰=外部依赖。

图表 brief：
{
  "id": "fig-8-3",
  "type": "flowchart",
  "title": "数据脱敏与匿名化决策流程",
  "purpose": "展示在数据发布前，如何根据数据敏感等级选择脱敏或匿名化策略，并最终通过重识别风险评估。",
  "audience_takeaway": "读者应理解数据脱敏与匿名化决策流程中的主链路、责任边界和工程取舍。",
  "visual_focus": "从id到from的主链路。",
  "layout": "自上而下的正交流程图",
  "components": [
    {
      "id": "c1",
      "label": "id",
      "type": "platform",
      "subtitle": "start",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "c2",
      "label": "id",
      "type": "platform",
      "subtitle": "classify",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c3",
      "label": "id",
      "type": "platform",
      "subtitle": "deidentify",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c4",
      "label": "id",
      "type": "platform",
      "subtitle": "branch",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c5",
      "label": "id",
      "type": "platform",
      "subtitle": "weak",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c6",
      "label": "id",
      "type": "platform",
      "subtitle": "strong",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c7",
      "label": "匿名 + 差分隐私注入）",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c8",
      "label": "id",
      "type": "platform",
      "subtitle": "risk",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c9",
      "label": "id",
      "type": "platform",
      "subtitle": "publish",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c10",
      "label": "from",
      "type": "platform",
      "subtitle": "start",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "from: start",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "from: classify",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c3",
      "to": "c4",
      "label": "from: classify",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c4",
      "to": "c5",
      "label": "from: deidentify",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c5",
      "to": "c6",
      "label": "from: branch",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c6",
      "to": "c7",
      "label": "from: branch",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c7",
      "to": "c8",
      "label": "from: weak",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c8",
      "to": "c9",
      "label": "from: strong",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c9",
      "to": "c10",
      "label": "from: risk",
      "style": "solid",
      "direction": "left-to-right"
    }
  ],
  "regions": [
    {
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    }
  ],
  "callouts": [
    "from: start",
    "from: classify",
    "from: classify"
  ],
  "legend": [
    "color: #gray",
    "color: #blue"
  ],
  "caption": "大多数项目的问题在于混淆脱敏和匿名化：做了一层掩盖就当成匿名化发布，导致重识别风险泄露。差异在于强匿名化必须通过重识别风险评估（资料：[S2]）。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "决策节点必须写成可判断的问题或动作，分支标签保持短句。"
  ]
}
