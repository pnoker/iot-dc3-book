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
  "id": "fig-2-5",
  "type": "sequence",
  "title": "图2-5 智能楼宇节能闭环的组件间交互时序示意图（假设场景）",
  "purpose": "帮助读者理解闭环模式下各组件之间的消息交互顺序、数据流转格式以及指令下行的协议翻译过程。",
  "audience_takeaway": "读者应理解智能楼宇节能闭环的组件间交互时序示意图（假设场景）中的主链路、责任边界和工程取舍。",
  "visual_focus": "从传感器/网关到发送动作序列指令的主链路。",
  "layout": "垂直时间轴序列图，从左到右排列六个泳道：传感器/网关、时序数据库、智能层（内部虚线分隔理解与决策）、指令调度器、空调设备。自上而下标注消息交互顺序。",
  "components": [
    {
      "id": "c1",
      "label": "传感器/网关",
      "type": "edge",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "c2",
      "label": "时序数据库",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "c3",
      "label": "智能层（理解/决策）",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "decision"
    },
    {
      "id": "c4",
      "label": "指令调度器",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "actor"
    },
    {
      "id": "c5",
      "label": "空调设备（两台）",
      "type": "edge",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c6",
      "label": "持续上报位号值流",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c7",
      "label": "查询过去1小时数据",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "c8",
      "label": "返回历史位号值JSON",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c9",
      "label": "输出状态摘要",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c10",
      "label": "发送动作序列指令",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "时序数据库同时接收写入（来自采集）…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "指令下行通道经过指令调度器完成协议…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c3",
      "to": "c4",
      "label": "执行完成后智能层设置定时器，标记下…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c4",
      "to": "c5",
      "label": "时序数据库同时接收写入（来自采集）…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c5",
      "to": "c6",
      "label": "指令下行通道经过指令调度器完成协议…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c6",
      "to": "c7",
      "label": "执行完成后智能层设置定时器，标记下…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c7",
      "to": "c8",
      "label": "时序数据库同时接收写入（来自采集）…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c8",
      "to": "c9",
      "label": "指令下行通道经过指令调度器完成协议…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c9",
      "to": "c10",
      "label": "执行完成后智能层设置定时器，标记下…",
      "style": "solid",
      "direction": "left-to-right"
    }
  ],
  "regions": [
    {
      "id": "edge_domain",
      "label": "设备与边缘域",
      "role": "现场异构资源边界"
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
    },
    {
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    }
  ],
  "callouts": [
    "时序数据库同时接收写入（来自采集）和响应读取（来自智能层）",
    "指令下行通道经过指令调度器完成协议翻译（抽象命令→Modbus寄存器写入）",
    "执行完成后智能层设置定时器，标记下一次闭环的开始"
  ],
  "legend": [
    "数据采集上行流",
    "理解阶段内部通信",
    "决策阶段内部通信",
    "指令下行与执行回执",
    "闭环回路箭头"
  ],
  "caption": "图2-5 智能楼宇节能闭环的组件间交互时序示意图（假设场景）",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
