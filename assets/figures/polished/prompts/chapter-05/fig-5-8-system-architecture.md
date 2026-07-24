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
  "id": "fig-5-8-system-architecture",
  "type": "architecture",
  "title": "工厂设备状态监控系统四层架构图（假设场景）",
  "purpose": "展示设备层、边缘层、消息层、云层四层架构，以及传感器数据从现场到告警的完整流经路径，包括本地紧急停机路径和云端AI分析路径。",
  "audience_takeaway": "读者应理解工厂设备状态监控系统四层架构图（假设场景）中的主链路、责任边界和工程取舍。",
  "visual_focus": "从起点到邮件/短信通知后采取行动的主链路。",
  "layout": "自上而下的四层结构，每层用浅色背景矩形框区分。层间箭头表示数据流方向，本地紧急停机路径用橙色粗箭头标出，与云端链路形成对比。",
  "components": [
    {
      "id": "r1",
      "label": "边缘层Node-RED解析并做两级…",
      "type": "edge",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "decision"
    },
    {
      "id": "r2",
      "label": "GPIO输出紧急停机信号（橙色箭头…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "AI服务从InfluxDB拉取最近…",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r4",
      "label": "Kafka的alarm-event…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "bus"
    },
    {
      "id": "r5",
      "label": "告警服务消费alarm-events",
      "type": "security",
      "group": "governance_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r6",
      "label": "SMTP和短信API发送通知",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r7",
      "label": "工程师通过Grafana查看仪表盘…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r8",
      "label": "邮件/短信通知后采取行动",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r9",
      "label": "云端下行指令（阈值更新、模型参数下…",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r10",
      "label": "Kafka的alarm-comma…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "bus"
    }
  ],
  "connections": [
    {
      "from": "node-red",
      "to": "gpio",
      "label": "橙色箭头，不经过消息层和云层",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "ai_influxdb_2",
      "to": "kafka_alarm-events_to",
      "label": "AI服务从InfluxDB拉取最近…",
      "style": "dashed",
      "direction": "event"
    },
    {
      "from": "r5",
      "to": "r6",
      "label": "告警服务消费alarm-event…",
      "style": "risk",
      "direction": "event"
    },
    {
      "from": "grafana",
      "to": "r8",
      "label": "工程师通过Grafana查看仪表盘…",
      "style": "solid",
      "direction": "request"
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
      "id": "intelligence_domain",
      "label": "智能决策域",
      "role": "模型、规则与 Agent 边界"
    },
    {
      "id": "governance_domain",
      "label": "治理与安全域",
      "role": "风险控制与责任边界"
    }
  ],
  "callouts": [
    "设备层通过Modbus RTU（9600bps）向边缘层推送传感器数据",
    "边缘层Node-RED解析并做两级阈值判断：超过一级阈值→GPIO输出紧急停机信号（橙色箭头，不经过消息层和云层）",
    "超过二级阈值或正常→发布MQTT消息至Mosquitto。同时写入SQLite缓存"
  ],
  "legend": [
    "实线箭头（浅灰）=传感器数据上行流",
    "实线箭头（橙色，加粗）=本地紧急停机控制流（不经过云端）",
    "虚线箭头（深灰）=告警事件下行流（通知工程师）",
    "虚线箭头（蓝色，虚线点划线）=云端指令下行流（远程控制参数）",
    "绿色圆点（在电机图标旁）=设备运行状态：正常",
    "黄色圆点=设备运行状态：预警（二级阈值触发）"
  ],
  "caption": "图5-8 工厂设备状态监控系统四层架构图（假设场景）",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
