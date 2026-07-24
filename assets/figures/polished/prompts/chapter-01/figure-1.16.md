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
  "id": "figure-1.16",
  "type": "matrix",
  "title": "实践建议优先级矩阵",
  "purpose": "将本章核心概念转化为5条可立即执行行动建议，并按投入产出和实施难度两个维度评估优先级，帮助读者快速决策从哪一条开始。",
  "audience_takeaway": "读者应理解实践建议优先级矩阵中的主链路、责任边界和工程取舍。",
  "visual_focus": "从建议编号到建议3：评估规则引擎承载极限的主链路。",
  "layout": "矩阵布局，按比较维度分组呈现。",
  "components": [
    {
      "id": "c1",
      "label": "建议编号",
      "type": "platform",
      "subtitle": "corner_header",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "c2",
      "label": "投入产出（价值/时间）",
      "type": "platform",
      "subtitle": "column_header",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c3",
      "label": "实施难度（低/中/高）",
      "type": "platform",
      "subtitle": "column_header",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c4",
      "label": "建议1：用三次浪潮框架重新定位项目",
      "type": "platform",
      "subtitle": "row_header",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c5",
      "label": "高——半天思考可避免数月技术路线错误",
      "type": "platform",
      "subtitle": "cell",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c6",
      "label": "低——仅需白板会议与团队讨论",
      "type": "platform",
      "subtitle": "cell",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c7",
      "label": "建议2：分隔感知值与推理值",
      "type": "ai",
      "subtitle": "row_header",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c8",
      "label": "高——为未来AI引入节省大量数据清…",
      "type": "data",
      "subtitle": "cell",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "c9",
      "label": "低-中——调整数据库设计即可",
      "type": "data",
      "subtitle": "cell",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "c10",
      "label": "建议3：评估规则引擎承载极限",
      "type": "platform",
      "subtitle": "row_header",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "每一行对应一条实践建议",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "第一列是投入产出评估，第二列是实施…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c3",
      "to": "c4",
      "label": "理想切入点：同时具备‘投入产出高’…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c4",
      "to": "c5",
      "label": "每一行对应一条实践建议",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c5",
      "to": "c6",
      "label": "第一列是投入产出评估，第二列是实施…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c6",
      "to": "c7",
      "label": "理想切入点：同时具备‘投入产出高’…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c7",
      "to": "c8",
      "label": "每一行对应一条实践建议",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c8",
      "to": "c9",
      "label": "第一列是投入产出评估，第二列是实施…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c9",
      "to": "c10",
      "label": "理想切入点：同时具备‘投入产出高’…",
      "style": "solid",
      "direction": "left-to-right"
    }
  ],
  "regions": [
    {
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    },
    {
      "id": "intelligence_domain",
      "label": "智能决策域",
      "role": "模型、规则与 Agent 边界"
    },
    {
      "id": "data_domain",
      "label": "数据资产域",
      "role": "数据沉淀与治理边界"
    }
  ],
  "callouts": [
    "每一行对应一条实践建议",
    "第一列是投入产出评估，第二列是实施难度评估",
    "理想切入点：同时具备‘投入产出高’和‘实施难度低’的条目"
  ],
  "legend": [
    "高投入产出或低实施难度",
    "中等投入产出或中等实施难度",
    "低投入产出或高实施难度"
  ],
  "caption": "图1-16 实践建议优先级矩阵。每个建议的投入产出和实施难度一目了然，优先从绿色单元格的条目开始。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
