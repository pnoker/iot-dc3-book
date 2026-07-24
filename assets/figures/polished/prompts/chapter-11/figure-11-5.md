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
  "id": "figure-11-5",
  "type": "architecture",
  "title": "城市物联网百万级接入系统架构图",
  "purpose": "展示百万级接入系统的拓扑结构，说明各层如何协同处理设备洪峰、实现水平扩展",
  "audience_takeaway": "读者应理解城市物联网百万级接入系统架构图中的主链路、责任边界和工程取舍。",
  "visual_focus": "从负载均衡器到设备层的主链路。",
  "layout": "left-to-right three-layer",
  "components": [
    {
      "id": "r1",
      "label": "负载均衡器",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "MQTT Broker集群",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "bus"
    },
    {
      "id": "r3",
      "label": "消息队列",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "bus"
    },
    {
      "id": "r4",
      "label": "流处理引擎",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r5",
      "label": "时序数据库",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "r6",
      "label": "业务微服务",
      "type": "application",
      "group": "application_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r7",
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
      "to": "r2",
      "label": "连接分配（IP哈希）",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r2",
      "to": "r3",
      "label": "消息发布",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r3",
      "to": "r4",
      "label": "数据消费（实时处理）",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r4",
      "to": "r5",
      "label": "写入聚合结果",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r3",
      "to": "r6",
      "label": "主题消费（非实时）",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r2",
      "to": "r7",
      "label": "心跳保活 / 订阅恢复",
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
      "id": "application_domain",
      "label": "业务应用域",
      "role": "业务价值交付边界"
    },
    {
      "id": "edge_domain",
      "label": "设备与边缘域",
      "role": "现场异构资源边界"
    }
  ],
  "callouts": [
    "负载均衡器 → MQTT Broker集群（连接分配（IP哈希））",
    "MQTT Broker集群 → 消息队列（消息发布）",
    "消息队列 → 流处理引擎（数据消费（实时处理））"
  ],
  "legend": [
    "实线箭头：数据流",
    "虚线箭头：控制流",
    "圆形节点：终端设备",
    "矩形节点：服务端组件",
    "菱形节点：消息队列"
  ],
  "caption": "图11-5 城市物联网百万级接入系统架构图。负载均衡器按IP哈希分配设备连接到MQTT Broker集群；Broker将消息发布到Kafka分区；流处理引擎从Kafka消费并处理后写入时序数据库；业务微服务直接从Kafka消费特定主题处理非实时数据；虚线控制流表示Broker向设备侧发送心跳和订阅恢复指令。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
