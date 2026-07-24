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
  "id": "fig-9-8-iot-standardization-timeline",
  "type": "timeline",
  "title": "图9-8 物联网标准化演进时间线",
  "purpose": "展示从标准割据到MCP统一语义的演进时间线，帮助读者理解阶段衔接与关键组织角色。",
  "audience_takeaway": "应理解标准化从垂直割据→水平整合→语义统一的三阶段主线，以及MCP在当前阶段的定位。",
  "visual_focus": "时间轴上的阶段分组框，以及表示融合关系的箭头，强调每个阶段标志性标准节点的连接。",
  "layout": "横向时间轴，自左至右分为三阶段，阶段间以虚线分隔。每个阶段内放置代表性标准节点，节点带名称。箭头从前一阶段节点指向后一阶段节点，标注融合关系。",
  "components": [
    {
      "id": "modbus",
      "label": "Modbus",
      "type": "application",
      "group": "stage_1_silo",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "zigbee",
      "label": "ZigBee",
      "type": "application",
      "group": "stage_1_silo",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "omadm",
      "label": "OMA DM",
      "type": "application",
      "group": "stage_1_silo",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "onem2m",
      "label": "oneM2M",
      "type": "platform",
      "group": "stage_2_integration",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "ietf_core",
      "label": "IETF CoRE",
      "type": "platform",
      "group": "stage_2_integration",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "w3c_wot",
      "label": "W3C WoT",
      "type": "platform",
      "group": "stage_3_semantic",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "mcp",
      "label": "MCP (当前趋势)",
      "type": "ai",
      "group": "stage_3_semantic",
      "priority": "primary",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "modbus",
      "to": "onem2m",
      "label": "接入抽象",
      "style": "dashed",
      "direction": "left-to-right"
    },
    {
      "from": "zigbee",
      "to": "onem2m",
      "label": "接入抽象",
      "style": "dashed",
      "direction": "left-to-right"
    },
    {
      "from": "omadm",
      "to": "onem2m",
      "label": "接入抽象",
      "style": "dashed",
      "direction": "left-to-right"
    },
    {
      "from": "onem2m",
      "to": "w3c_wot",
      "label": "语义对齐",
      "style": "dashed",
      "direction": "left-to-right"
    },
    {
      "from": "ietf_core",
      "to": "w3c_wot",
      "label": "语义对齐",
      "style": "dashed",
      "direction": "left-to-right"
    },
    {
      "from": "w3c_wot",
      "to": "mcp",
      "label": "融合演进",
      "style": "solid",
      "direction": "left-to-right"
    }
  ],
  "regions": [
    {
      "id": "stage_1_silo",
      "label": "标准割据期 (2000-2010，示意)",
      "role": "垂直标准各行其是"
    },
    {
      "id": "stage_2_integration",
      "label": "联盟整合期 (2010-2018，示意)",
      "role": "水平平台与资源模型搭建"
    },
    {
      "id": "stage_3_semantic",
      "label": "语义互操作期 (2018-，示意)",
      "role": "语义本体与AI交互展开"
    }
  ],
  "callouts": [
    "阶段变化代表标准化层次从语法到语义的提升。",
    "MCP 是现有标准的融合体，而非从零制定的新协议。"
  ],
  "legend": [
    "灰色：垂直领域标准（割据期）",
    "蓝色：水平平台/中间层（整合期）",
    "橙色：语义互操作与AI交互（语义期）",
    "青色：MCP（当前趋势）"
  ],
  "caption": "图9-8 物联网标准化演进时间线（基于公开标准信息整理，时间范围与阶段起止年为示意性节点划分）。",
  "visual_constraints": [
    "最多 7 个节点，标签简短。",
    "箭头标签不超过 5 个汉字。"
  ]
}
