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
  "id": "fig-7-4-function-calling-flow",
  "type": "sequence",
  "title": "图7-4 Function Calling 交互流程：从自然语言到设备操作",
  "purpose": "展示 Spring AI Function Calling 的完整调用链路，以“关A区灯”为例，说明操作员、ChatClient、LLM、LightTool 之间的消息交换顺序。",
  "audience_takeaway": "读者应理解Function Calling 交互流程：从自然语言到设备操作中的主链路、责任边界和工程取舍。",
  "visual_focus": "从操作员到终点的主链路。",
  "layout": "纵向顺序排列参与者，箭头从上至下表示时序。",
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
      "label": "ChatClient: 发送请求",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "ChatClient",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r4",
      "label": "LLM: 发送消息+Tool定义",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "bus"
    },
    {
      "id": "r5",
      "label": "LLM",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r6",
      "label": "ChatClient: 返回JSO…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r7",
      "label": "LightTool: 调用togg…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r8",
      "label": "LightTool",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r9",
      "label": "ChatClient: 返回执行结果",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r10",
      "label": "LLM: 发送结果",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "r1",
      "to": "r2",
      "label": "操作员 -> ChatClient…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r3",
      "to": "r4",
      "label": "ChatClient -> LLM…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r5",
      "to": "chatclient_json",
      "label": "LLM -> ChatClient…",
      "style": "dashed",
      "direction": "response"
    },
    {
      "from": "r3",
      "to": "lighttool_toggleli",
      "label": "ChatClient -> Lig…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r8",
      "to": "r9",
      "label": "LightTool -> Chat…",
      "style": "dashed",
      "direction": "response"
    },
    {
      "from": "r3",
      "to": "r10",
      "label": "ChatClient -> LLM…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r5",
      "to": "chatclient",
      "label": "LLM -> ChatClient…",
      "style": "dashed",
      "direction": "response"
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
    }
  ],
  "callouts": [
    "操作员 -> ChatClient: 发送请求",
    "ChatClient -> LLM: 发送消息+Tool定义",
    "LLM -> ChatClient: 返回JSON函数调用"
  ],
  "legend": [
    "实线箭头：同步请求/调用",
    "虚线箭头：同步返回/响应",
    "左上方参与者为操作员，左中心为ChatClient，中心为LLM，右侧为LightTool Bean"
  ],
  "caption": "图7-4 展示了 Spring AI Function Calling 的完整调用链路，以“关A区灯”为例。操作员的自然语言请求首先到达 ChatClient，ChatClient 将消息连同 LightTool 的工具描述发送给 LLM。LLM 推理后返回 JSON 格式的函数调用请求，ChatClient 解析并调用对应的 @Tool 方法，将执行结果回填给 LLM 后，LLM 生成最终的自然语言回复返回给操作员。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
