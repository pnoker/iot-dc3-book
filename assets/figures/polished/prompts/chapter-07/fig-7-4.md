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
  "id": "fig-7-4",
  "type": "dataflow",
  "title": "图7-4 RAG + Tool-Calling 联合工作流",
  "purpose": "展示一个运维任务从用户发起到 LLM 推理、RAG 检索、Tool-Calling 执行直至设备响应的完整数据流向和职责划分。",
  "audience_takeaway": "读者应理解RAG + Tool-Calling 联合工作流中的主链路、责任边界和工程取舍。",
  "visual_focus": "从操作员到终点的主链路。",
  "layout": "水平泳道布局，从上到下四条泳道：用户层、AI 推理层、知识检索层、设备执行层。",
  "components": [
    {
      "id": "r1",
      "label": "操作员",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "LLM 推理引擎：发起任务（自然语…",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "LLM 推理引擎",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r4",
      "label": "向量知识库：检索 SOP 文档，实…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r5",
      "label": "向量知识库",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r6",
      "label": "LLM 推理引擎：返回 SOP 文…",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r7",
      "label": "Tool-Calling 执行器…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r8",
      "label": "Tool-Calling 执行器",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r9",
      "label": "设备层：下发关泵指令，虚线箭头",
      "type": "edge",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r10",
      "label": "设备层",
      "type": "edge",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "r1",
      "to": "llm",
      "label": "操作员 → LLM 推理引擎：发起…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r3",
      "to": "sop",
      "label": "LLM 推理引擎 → 向量知识库…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r5",
      "to": "llm_sop",
      "label": "向量知识库 → LLM 推理引擎…",
      "style": "dashed",
      "direction": "response"
    },
    {
      "from": "r3",
      "to": "tool-calling_so",
      "label": "LLM 推理引擎 → Tool-C…",
      "style": "dashed",
      "direction": "request"
    },
    {
      "from": "r8",
      "to": "r9",
      "label": "Tool-Calling 执行器…",
      "style": "dashed",
      "direction": "request"
    },
    {
      "from": "r10",
      "to": "tool-calling",
      "label": "设备层 → Tool-Callin…",
      "style": "dashed",
      "direction": "response"
    },
    {
      "from": "r8",
      "to": "llm",
      "label": "Tool-Calling 执行器…",
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
      "id": "intelligence_domain",
      "label": "智能决策域",
      "role": "模型、规则与 Agent 边界"
    },
    {
      "id": "edge_domain",
      "label": "设备与边缘域",
      "role": "现场异构资源边界"
    }
  ],
  "callouts": [
    "操作员 → LLM 推理引擎：发起任务（自然语言），实线箭头",
    "LLM 推理引擎 → 向量知识库：检索 SOP 文档，实线箭头",
    "向量知识库 → LLM 推理引擎：返回 SOP 文档（步骤 A、B、C），实线箭头"
  ],
  "legend": [
    "蓝色实线箭头：RAG 检索路径（知识获取）",
    "绿色虚线箭头：工具调用路径（操作执行）",
    "水平虚线：泳道分隔线，颜色 #cccccc，描边宽度 1px"
  ],
  "caption": "图7-4 RAG + Tool-Calling 联合工作流图。操作员发起任务后，LLM 首先通过 RAG 检索设备 SOP 文档，获取操作步骤；随后按步骤依次调用 Tool-Calling 执行具体设备操作，直至任务完成。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
