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
  "id": "fig-7-3",
  "type": "architecture",
  "title": "图7-3 ReAct 循环在物联网 Agent 中的工作示意",
  "purpose": "展示 Agent 如何通过思考-行动-观察的循环完成多步运维任务。",
  "audience_takeaway": "读者应理解 ReAct 循环中思考、行动、观察三个环节的交替逻辑，以及完成判断与结果输出之间的关系。",
  "visual_focus": "从用户输入到结果输出的主链路，重点突出循环回退路径。",
  "layout": "水平居中，三个主要节点‘思考’‘行动’‘观察’呈三角形排列，用带箭头的循环线连接，最终从‘是否完成’判断节点指向‘结果输出’。",
  "components": [
    {
      "id": "user_input",
      "label": "用户输入",
      "type": "application",
      "subtitle": "自然语言指令",
      "group": "user_domain",
      "priority": "primary",
      "shape": "actor"
    },
    {
      "id": "thought",
      "label": "思考",
      "type": "ai",
      "subtitle": "推理：判断下一步",
      "group": "agent_loop_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "action",
      "label": "行动",
      "type": "platform",
      "subtitle": "调用工具",
      "group": "agent_loop_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "observation",
      "label": "观察",
      "type": "data",
      "subtitle": "接收工具返回结果",
      "group": "agent_loop_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "done_check",
      "label": "是否完成",
      "type": "decision",
      "subtitle": "子任务是否完成？",
      "group": "decision_domain",
      "priority": "normal",
      "shape": "decision"
    },
    {
      "id": "final_output",
      "label": "结果输出",
      "type": "application",
      "subtitle": "最终答案",
      "group": "user_domain",
      "priority": "primary",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "user_input",
      "to": "thought",
      "label": "解析目标",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "thought",
      "to": "action",
      "label": "决定工具",
      "style": "solid",
      "direction": "right"
    },
    {
      "from": "action",
      "to": "observation",
      "label": "返回数据",
      "style": "dashed",
      "direction": "right"
    },
    {
      "from": "observation",
      "to": "thought",
      "label": "评估结果",
      "style": "solid",
      "direction": "left"
    },
    {
      "from": "thought",
      "to": "done_check",
      "label": "循环后检查",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "done_check",
      "to": "thought",
      "label": "继续循环",
      "style": "dashed",
      "direction": "right"
    },
    {
      "from": "done_check",
      "to": "final_output",
      "label": "完成",
      "style": "solid",
      "direction": "bottom-to-top"
    }
  ],
  "regions": [
    {
      "id": "user_domain",
      "label": "用户交互域",
      "role": "指令输入与结果接收边界"
    },
    {
      "id": "agent_loop_domain",
      "label": "Agent 内部循环域",
      "role": "思考-行动-观察循环的职责边界"
    },
    {
      "id": "decision_domain",
      "label": "完成判断域",
      "role": "循环是否结束的判定边界"
    }
  ],
  "callouts": [
    "思考→行动→观察→思考 构成闭环，直到完成条件满足。",
    "虚线箭头表示可选择的回退路径，实线箭头表示确定性流转。"
  ],
  "legend": [
    "圆形：用户交互边界",
    "蓝色：AI 推理节点",
    "绿色：工具调用节点",
    "黄色：数据观测节点",
    "菱形：判断决策",
    "实线箭头：主路径；虚线箭头：循环回退"
  ],
  "caption": "图7-3  ReAct 循环在物联网 Agent 中的工作示意，展示自然语言指令如何通过推理-行动-观察循环完成多步任务。",
  "visual_constraints": [
    "节点标签使用短名词，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "循环箭头使用三角形回流线，避免交叉。"
  ]
}
