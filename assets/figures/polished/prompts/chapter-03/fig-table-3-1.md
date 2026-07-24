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
  "id": "fig-table-3-1",
  "type": "matrix",
  "title": "常用传感器类型、原理与典型应用",
  "purpose": "快速对照传感器类别、传感原理和常见部署场景",
  "audience_takeaway": "读者应理解常用传感器类型、原理与典型应用中的主链路、责任边界和工程取舍。",
  "visual_focus": "从进入下一判断到进入下一判断的主链路。",
  "layout": "8行 × 4列（含表头行）。标题行加粗，单元格内文本左对齐。表头背景色浅灰。",
  "components": [
    {
      "id": "c1",
      "label": "进入下一判断",
      "type": "platform",
      "subtitle": "row",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "c2",
      "label": "进入下一判断",
      "type": "platform",
      "subtitle": "row",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c3",
      "label": "进入下一判断",
      "type": "platform",
      "subtitle": "row",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c4",
      "label": "进入下一判断",
      "type": "platform",
      "subtitle": "row",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c5",
      "label": "进入下一判断",
      "type": "platform",
      "subtitle": "row",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c6",
      "label": "进入下一判断",
      "type": "platform",
      "subtitle": "row",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c7",
      "label": "进入下一判断",
      "type": "platform",
      "subtitle": "row",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c8",
      "label": "进入下一判断",
      "type": "platform",
      "subtitle": "row",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c9",
      "label": "进入下一判断",
      "type": "platform",
      "subtitle": "row",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "horizontal",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "horizontal",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c3",
      "to": "c4",
      "label": "horizontal",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c4",
      "to": "c5",
      "label": "horizontal",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c5",
      "to": "c6",
      "label": "horizontal",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c6",
      "to": "c7",
      "label": "horizontal",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c7",
      "to": "c8",
      "label": "horizontal",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c8",
      "to": "c9",
      "label": "horizontal",
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
    "horizontal"
  ],
  "legend": [
    "无图例。"
  ],
  "caption": "选型注意点归纳了该原理传感器在工程现场最常遇到的工程陷阱，供选型时权衡。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
