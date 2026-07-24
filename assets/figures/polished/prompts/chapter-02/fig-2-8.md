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
  "id": "fig-2-8",
  "type": "dataflow",
  "title": "Data中心数据流示意：从设备采集到时序存储",
  "purpose": "展示IoT DC3 Data中心的核心数据流，说明从设备到时序存储的完整路径，以及消息队列如何缓冲和解耦。",
  "audience_takeaway": "读者应理解Data中心数据流示意：从设备采集到时序存储中的主链路、责任边界和工程取舍。",
  "visual_focus": "从现场设备到订阅方（监控/Agentic/告警）的主链路。",
  "layout": "horizontal_left_to_right",
  "components": [
    {
      "id": "device",
      "label": "现场设备",
      "type": "edge",
      "subtitle": "物理设备，如PLC、电表、传感器",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "driver",
      "label": "驱动 dc3-driver-*",
      "type": "platform",
      "subtitle": "南向协议驱动，将原始信号归一为PointVal…",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "gateway",
      "label": "Gateway",
      "type": "platform",
      "subtitle": "唯一对外HTTP入口，完成鉴权与路由",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "datacenter",
      "label": "Data中心 dc3-center…",
      "type": "data",
      "subtitle": "负责数据接收、缓冲与分发的核心服务",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "mq",
      "label": "RabbitMQ 消息队列",
      "type": "platform",
      "subtitle": "异步缓冲层，削峰填谷，解耦写入与消费",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "bus"
    },
    {
      "id": "store",
      "label": "时序数据库 TimescaleDB",
      "type": "data",
      "subtitle": "持久化存储，支持时间范围查询与聚合",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "consumer",
      "label": "订阅方（监控/Agentic/告警）",
      "type": "data",
      "subtitle": "消费数据的下游服务",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    }
  ],
  "connections": [
    {
      "from": "device",
      "to": "driver",
      "label": "数据从左到右流动：设备→驱动→Ga…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "driver",
      "to": "gateway",
      "label": "数据从左到右流动：设备→驱动→Ga…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "gateway",
      "to": "datacenter",
      "label": "数据从左到右流动：设备→驱动→Ga…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "datacenter",
      "to": "mq",
      "label": "数据从左到右流动：设备→驱动→Ga…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "mq",
      "to": "store",
      "label": "数据从左到右流动：设备→驱动→Ga…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "store",
      "to": "consumer",
      "label": "数据从左到右流动：设备→驱动→Ga…",
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
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    },
    {
      "id": "data_domain",
      "label": "数据资产域",
      "role": "数据沉淀与治理边界"
    }
  ],
  "callouts": [
    "数据从左到右流动：设备→驱动→Gateway→Data中心→消息队列→时序数据库，同时消息队列将数据分发到订阅方…"
  ],
  "legend": [
    "device=蓝色 (#4A90D9)",
    "driver=橙色 (#E67E22)",
    "gateway=绿色 (#27AE60)",
    "datacenter=紫色 (#8E44AD)",
    "queue=灰色 (#7F8C8D)",
    "store=黄色 (#F1C40F)"
  ],
  "caption": "Data中心数据流示意图",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
