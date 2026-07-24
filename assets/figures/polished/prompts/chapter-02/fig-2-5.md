请按 architecture-diagram 技能的出版级暗色技术图风格，重绘下面这张书籍插图。

硬性要求：
1. 输出 self-contained HTML，主体为 inline SVG；同时导出同名 SVG 与 PNG。
2. 画布建议 1600×1000 或 1800×1100，暗色背景、细网格、圆角卡片、清晰箭头、图例置于边界外。
3. 节点短标签优先，解释写入 callouts；禁止“节点1/节点2/container/service/user”等占位词。
4. 每张图只表达一个主结论，主链路高亮，边界、层级、时序或决策关系必须一眼可读。
5. 中文字体使用系统无衬线或 JetBrains Mono fallback；PNG 需适合 Word 印刷，文字不得重叠或过小。
6. 保持全书统一视觉语义：蓝=核心平台，青绿=边缘/接入，橙=AI/智能，紫=数据，红=安全/风险，灰=外部依赖。

图表 brief：
{
  "id": "fig-2-5",
  "type": "architecture",
  "title": "图2-5 IoT DC3 五大中心逻辑关系",
  "purpose": "展示 Gateway、Auth、Manager、Data、Agentic 五个微服务之间的调用依赖和数据流向，以及它们与外部基础设施（消息队列、时序数据库）的关系。",
  "audience_takeaway": "读者应理解IoT DC3 五大中心逻辑关系中的主链路、责任边界和工程取舍。",
  "visual_focus": "从Gateway 中心通过 REST到终点的主链路。",
  "layout": "layered-top-down",
  "components": [
    {
      "id": "r1",
      "label": "Gateway 中心通过 REST",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "Auth 中心进行令牌校验",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "Manager 中心查询元数据",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "r4",
      "label": "Data 中心进行数据查询和命令下发",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "r5",
      "label": "Agentic 中心发起 AI 请求",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r6",
      "label": "Agentic 中心通过 REST",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r7",
      "label": "Data 中心进行位号查询和命令执…",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r8",
      "label": "Manager 中心查询元数据（虚…",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    }
  ],
  "connections": [
    {
      "from": "r1",
      "to": "r2",
      "label": "Gateway 中心通过 REST…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r1",
      "to": "r3",
      "label": "Gateway 中心通过 REST…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r1",
      "to": "r4",
      "label": "Gateway 中心通过 REST…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r1",
      "to": "r5",
      "label": "Gateway 中心通过 REST…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r6",
      "to": "data",
      "label": "Agentic 中心通过 REST…",
      "style": "dashed",
      "direction": "request"
    },
    {
      "from": "r6",
      "to": "manager",
      "label": "Agentic 中心通过 REST…",
      "style": "dashed",
      "direction": "request"
    }
  ],
  "regions": [
    {
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    },
    {
      "id": "data_domain",
      "label": "数据资产域",
      "role": "数据沉淀与治理边界"
    },
    {
      "id": "intelligence_domain",
      "label": "智能决策域",
      "role": "模型、规则与 Agent 边界"
    }
  ],
  "callouts": [
    "Gateway 中心通过 REST 调用 Auth 中心进行令牌校验",
    "Gateway 中心通过 REST 调用 Manager 中心查询元数据",
    "Gateway 中心通过 REST 调用 Data 中心进行数据查询和命令下发"
  ],
  "legend": [
    "实线矩形节点: DC3 微服务节点。",
    "虚线矩形节点: 外部基础设施。",
    "实线箭头: REST API 调用。",
    "虚线箭头: Agentic 中心发起的内部 REST 调用。",
    "双线箭头: AMQP 消息（双向）。",
    "箭头标签: 标注了调用的协议或目的。"
  ],
  "caption": "图 2-5 IoT DC3 五大中心逻辑关系。Gateway 是北向唯一入口，Auth 提供鉴权上下文，Manager 提供元数据，Data 是数据核心枢纽，Agentic 是 AI 能力层。数据经由消息队列解耦采集与命令下发。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
