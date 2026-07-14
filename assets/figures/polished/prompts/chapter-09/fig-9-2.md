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
  "id": "fig-9-2",
  "type": "dataflow",
  "title": "MQTT 发布/订阅模型与内部机制",
  "purpose": "说明 MQTT 发布/订阅模型中各组件间的消息流动，包括 QoS 处理、保留消息和遗嘱消息机制。",
  "audience_takeaway": "读者应理解MQTT 发布/订阅模型与内部机制中的主链路、责任边界和工程取舍。",
  "visual_focus": "从发布者将消息发送到终点的主链路。",
  "layout": "分层数据流图：从左到右依次为发布者、Broker、订阅者。Broker 内部拆分为主题树匹配模块、QoS 状态机（0/1/2）、保留消息缓存区、遗嘱消息控制器。",
  "components": [
    {
      "id": "r1",
      "label": "发布者将消息发送",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "bus"
    },
    {
      "id": "r2",
      "label": "Broker，Broker 内的主…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "新订阅者",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r4",
      "label": "时，Broker 查询保留消息缓存…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "bus"
    },
    {
      "id": "r5",
      "label": "Broker 通过心跳超时检测",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r6",
      "label": "客户端异常断开后，立即从遗嘱队列中…",
      "type": "security",
      "group": "governance_domain",
      "priority": "normal",
      "shape": "bus"
    }
  ],
  "connections": [
    {
      "from": "r1",
      "to": "broker_broker",
      "label": "发布者将消息发送到 Broker…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r3",
      "to": "broker",
      "label": "新订阅者连接时，Broker 查询…",
      "style": "solid",
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
      "id": "governance_domain",
      "label": "治理与安全域",
      "role": "风险控制与责任边界"
    }
  ],
  "callouts": [
    "发布者将消息发送到 Broker，Broker 内的主题树根据订阅者注册的过滤器（含通配符）匹配出目标订阅者集合",
    "对于 QoS 1/2 消息，Broker 启动相应握手状态机",
    "对于 retain=1 的消息，Broker 更新缓存区中的最新值"
  ],
  "legend": [
    "实线箭头：常规消息流",
    "虚线箭头：遗嘱消息流",
    "蓝色框：QoS 0 处理模块",
    "绿色框：QoS 1 处理模块",
    "橙色框：QoS 2 处理模块",
    "紫色框：保留消息缓存区"
  ],
  "caption": "图9-2 MQTT 发布/订阅模型与内部机制",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
