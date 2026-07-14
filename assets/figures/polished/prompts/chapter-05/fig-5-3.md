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
  "id": "fig-5-3",
  "type": "dataflow",
  "title": "图5-3 消息队列缓冲削峰示意",
  "purpose": "说明消息队列在设备洪峰到来时如何暂存消息，防止后端处理系统过载。",
  "audience_takeaway": "读者应理解消息队列缓冲削峰示意中的主链路、责任边界和工程取舍。",
  "visual_focus": "从设备群到时间轴的主链路。",
  "layout": "从左到右数据流：设备群→Topic分区→消费者组→后端服务。时间轴上展示瞬时流量尖峰和队列水位变化。",
  "components": [
    {
      "id": "device_group",
      "label": "设备群",
      "type": "edge",
      "subtitle": "传感器、PLC等数据源",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "database"
    },
    {
      "id": "topic_partition",
      "label": "Topic分区",
      "type": "platform",
      "subtitle": "Kafka分区结构",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "bus"
    },
    {
      "id": "consumer_group",
      "label": "消费者组",
      "type": "platform",
      "subtitle": "C1, C2, C3实例",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "backend",
      "label": "后端服务",
      "type": "data",
      "subtitle": "告警引擎、时序库、降采样",
      "group": "data_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "timeline",
      "label": "时间轴",
      "type": "platform",
      "subtitle": "正常与洪峰阶段",
      "group": "platform_domain",
      "priority": "supporting",
      "shape": "boundary"
    }
  ],
  "connections": [
    {
      "from": "device_group",
      "to": "topic_partition",
      "label": "数据上报",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "topic_partition",
      "to": "consumer_group",
      "label": "负载均衡",
      "style": "dashed",
      "direction": "left-to-right"
    },
    {
      "from": "consumer_group",
      "to": "backend",
      "label": "消费输出",
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
    "洪峰期间队列水位升高，消费者按能力拉取，后端不受瞬时冲击。",
    "多个消费者组可独立消费同一Topic，满足不同处理时效要求。"
  ],
  "legend": [
    "青绿色=数据源；蓝色=消息队列与消费者；灰色=后端服务；实线=直接数据流；虚线=调度/分配关系；粗箭头=高流量。"
  ],
  "caption": "图5-3 消息队列缓冲削峰示意：洪峰到达时，消息在Topic分区中暂存，消费者组按积压数据逐步消费，后端服务不直接承受瞬时冲击。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
