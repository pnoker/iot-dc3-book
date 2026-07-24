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
  "id": "fig-11-5",
  "type": "architecture",
  "title": "图11-5 城市物联网消息队列与数据流处理架构",
  "purpose": "展示从设备层到最终数据消费的完整消息流转路径，突出消息队列作为缓冲和分发枢纽，以及流处理引擎如何实现数据精炼。",
  "audience_takeaway": "读者应理解城市物联网消息队列与数据流处理架构中的主链路、责任边界和工程取舍——设备接入、消息缓冲、流式计算、存储/服务四层职责清晰。",
  "visual_focus": "从设备层经Kafka/RocketMQ到达Flink/Spark流处理层的主链路，以及可选归档路径。",
  "layout": "自上而下四层：设备层→消息队列层→流处理层→存储与服务层。",
  "components": [
    {
      "id": "device_lamp",
      "label": "智能路灯",
      "type": "edge",
      "subtitle": "照明/环境检测",
      "group": "device_layer",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "device_rsu",
      "label": "路口RSU",
      "type": "edge",
      "subtitle": "信号灯/车流",
      "group": "device_layer",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "device_obu",
      "label": "网联汽车",
      "type": "edge",
      "subtitle": "GPS/状态",
      "group": "device_layer",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "device_env",
      "label": "环境传感器",
      "type": "edge",
      "subtitle": "空气/噪音",
      "group": "device_layer",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "kafka_traffic",
      "label": "Kafka: traffic_raw",
      "type": "platform",
      "subtitle": "高吞吐时序管道",
      "group": "mq_layer",
      "priority": "primary",
      "shape": "bus"
    },
    {
      "id": "kafka_env",
      "label": "Kafka: env_raw",
      "type": "platform",
      "subtitle": "传感器状态管道",
      "group": "mq_layer",
      "priority": "normal",
      "shape": "bus"
    },
    {
      "id": "rocketmq_cmd",
      "label": "RocketMQ: cmd",
      "type": "platform",
      "subtitle": "事务性控制指令",
      "group": "mq_layer",
      "priority": "normal",
      "shape": "bus"
    },
    {
      "id": "flink_traffic",
      "label": "Flink交通聚合",
      "type": "ai",
      "subtitle": "5min窗口车流量",
      "group": "stream_layer",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "flink_env",
      "label": "Flink环境检测",
      "type": "ai",
      "subtitle": "实时阈值/模型",
      "group": "stream_layer",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "spark_energy",
      "label": "Spark能耗统计",
      "type": "platform",
      "subtitle": "微批次调光优化",
      "group": "stream_layer",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "redis_cache",
      "label": "Redis缓存",
      "type": "data",
      "subtitle": "路口状态/配置",
      "group": "storage_layer",
      "priority": "primary",
      "shape": "database"
    },
    {
      "id": "tsdb_store",
      "label": "时序数据库",
      "type": "data",
      "subtitle": "历史轨迹/趋势",
      "group": "storage_layer",
      "priority": "primary",
      "shape": "database"
    }
  ],
  "connections": [
    {
      "from": "device_lamp",
      "to": "kafka_traffic",
      "label": "照明/环境",
      "style": "solid",
      "direction": "top-to-bottom"
    },
    {
      "from": "device_rsu",
      "to": "kafka_traffic",
      "label": "车流/相位",
      "style": "solid",
      "direction": "top-to-bottom"
    },
    {
      "from": "device_obu",
      "to": "kafka_traffic",
      "label": "GPS/状态",
      "style": "solid",
      "direction": "top-to-bottom"
    },
    {
      "from": "device_env",
      "to": "kafka_env",
      "label": "空气/噪音",
      "style": "solid",
      "direction": "top-to-bottom"
    },
    {
      "from": "kafka_traffic",
      "to": "flink_traffic",
      "label": "消费",
      "style": "solid",
      "direction": "top-to-bottom"
    },
    {
      "from": "kafka_env",
      "to": "flink_env",
      "label": "消费",
      "style": "solid",
      "direction": "top-to-bottom"
    },
    {
      "from": "kafka_traffic",
      "to": "spark_energy",
      "label": "可选消费",
      "style": "dashed",
      "direction": "top-to-bottom"
    },
    {
      "from": "flink_traffic",
      "to": "redis_cache",
      "label": "写入",
      "style": "solid",
      "direction": "top-to-bottom"
    },
    {
      "from": "flink_traffic",
      "to": "tsdb_store",
      "label": "归档",
      "style": "solid",
      "direction": "top-to-bottom"
    },
    {
      "from": "flink_env",
      "to": "tsdb_store",
      "label": "报警写入",
      "style": "solid",
      "direction": "top-to-bottom"
    },
    {
      "from": "kafka_traffic",
      "to": "ai_microservice",
      "label": "可选消费",
      "style": "dashed",
      "direction": "top-to-bottom"
    },
    {
      "from": "rocketmq_cmd",
      "to": "ai_microservice",
      "label": "控制指令",
      "style": "solid",
      "direction": "top-to-bottom"
    }
  ],
  "regions": [
    {
      "id": "device_layer",
      "label": "设备与边缘域",
      "role": "现场数据生产者"
    },
    {
      "id": "mq_layer",
      "label": "消息队列域",
      "role": "缓冲与分发枢纽"
    },
    {
      "id": "stream_layer",
      "label": "流处理域",
      "role": "实时清洗与聚合"
    },
    {
      "id": "storage_layer",
      "label": "存储与服务域",
      "role": "持久化与智能决策"
    }
  ],
  "callouts": [
    "消息队列作为缓冲层，允许消费端随意增减而不影响设备端写入。",
    "Flink检查点机制保证精确一次语义，是工程可恢复性的核心。",
    "Kafka traffic_raw Topic同时被Flink和Spark消费，体现了数据的单流多消费能力。"
  ],
  "legend": [
    "蓝色=平台层组件；青绿色=设备与边缘；橙色=AI/流处理；灰色=数据存储",
    "实线箭头=主要数据流；虚线箭头=可选/归档路径"
  ],
  "caption": "图11-5 展示设备层、消息队列、流处理层与存储服务层之间的数据流动。设备上报到Kafka，Flink消费后聚合写入Redis/时序DB；AI推理微服务通过RocketMQ接收控制指令。",
  "visual_constraints": [
    "最多15个组件，跨四层；主要关注Kafka-traffic→Flink→Redis/TSDB的主链路。",
    "图例在底部，不遮挡主体。",
    "使用圆角矩形图标，箭头带短标签。"
  ]
}
