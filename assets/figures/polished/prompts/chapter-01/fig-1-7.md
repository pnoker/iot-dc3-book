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
  "id": "fig-1-7",
  "type": "flowchart",
  "title": "图1-7 传统物联网与大模型驱动物联网的对比",
  "purpose": "直观对比两种物联网模式的决策链路与用户交互路径，突出大模型引入推理能力带来的架构变化。",
  "audience_takeaway": "读者应理解传统物联网与大模型驱动物联网的对比中的主链路、责任边界和工程取舍。",
  "visual_focus": "从大模型驱动物联网：用户自然语言描述到终点的主链路。",
  "layout": "左右两列，每列从上到下分三层：用户交互层、决策层、执行层。左侧为传统物联网，右侧为大模型驱动物联网。两列之间用箭头标识转变方向，底部标注关键差异。",
  "components": [
    {
      "id": "r1",
      "label": "传统物联网：用户输入固定指令",
      "type": "application",
      "group": "application_domain",
      "priority": "primary",
      "shape": "actor"
    },
    {
      "id": "r2",
      "label": "规则引擎精确匹配 → 直接执行或报…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "大模型驱动物联网：用户自然语言描述",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "actor"
    },
    {
      "id": "r4",
      "label": "LLM解析意图并查询设备实时状态…",
      "type": "edge",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "r3",
      "to": "llm",
      "label": "大模型驱动物联网：用户自然语言描述…",
      "style": "dashed",
      "direction": "request"
    }
  ],
  "regions": [
    {
      "id": "application_domain",
      "label": "业务应用域",
      "role": "业务价值交付边界"
    },
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
    "传统物联网：用户输入固定指令 → 规则引擎精确匹配 → 直接执行或报警（反馈为闭环箭头）",
    "大模型驱动物联网：用户自然语言描述 → LLM解析意图并查询设备实时状态 → 生成决策序列 → 用户二次确认后执行…"
  ],
  "legend": [
    "矩形框：用户交互节点",
    "钻石框：决策节点（规则引擎或LLM）",
    "圆形：设备节点",
    "黄色椭圆：用户确认节点",
    "实线箭头：确定性指令/数据流向",
    "虚线箭头：基于概率的推荐路径"
  ],
  "caption": "图1-7 传统物联网与大模型驱动物联网的对比示意。左侧为规则驱动的“感知-响应”模式，右侧为推理驱动的“理解-决策-确认”模式。大模型在决策层增加上下文理解和概率推理的能力，同时引入了执行前二次确认的安全机制。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "决策节点必须写成可判断的问题或动作，分支标签保持短句。"
  ]
}
