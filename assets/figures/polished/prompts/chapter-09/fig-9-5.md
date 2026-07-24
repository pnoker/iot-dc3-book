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
  "id": "fig-9-5",
  "type": "sequence",
  "title": "图9-5 MQTT智能家居监控系统交互序列",
  "purpose": "展示MQTT在智能家居温湿度监控场景中的完整交互时序，包括连接建立、数据发布、告警触发以及断连后遗嘱消息的发布流程。",
  "audience_takeaway": "读者应理解MQTT设备、Broker、订阅端和手机App之间的消息时序，重点关注遗嘱消息和QoS 2告警消息在可靠性保障中的角色。",
  "visual_focus": "设备到Broker到订阅端的数据发布链路（蓝色虚线），以及断连后Broker发布的遗嘱消息（红色虚线）。",
  "layout": "水平泳道，时间轴自上而下，分三个Phase阶段。",
  "components": [
    {
      "id": "sensor",
      "label": "传感器设备",
      "type": "edge",
      "subtitle": "MQTT Client",
      "group": "phase_i",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "broker",
      "label": "MQTT Broker",
      "type": "platform",
      "subtitle": "消息路由",
      "group": "phase_i",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "cloud_sub",
      "label": "云平台订阅端",
      "type": "application",
      "subtitle": "MQTT Client",
      "group": "phase_ii",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "phone_app",
      "label": "手机App",
      "type": "application",
      "subtitle": "告警接收",
      "group": "phase_ii",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "network_fail",
      "label": "网络故障",
      "type": "external",
      "subtitle": "中断事件",
      "group": "phase_iii",
      "priority": "risk",
      "shape": "boundary"
    }
  ],
  "connections": [
    {
      "from": "sensor",
      "to": "broker",
      "label": "CONNECT (含遗嘱)",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "broker",
      "to": "sensor",
      "label": "CONNACK",
      "style": "solid",
      "direction": "response"
    },
    {
      "from": "sensor",
      "to": "broker",
      "label": "PUBLISH 温度 (qos=1)",
      "style": "dashed",
      "direction": "request"
    },
    {
      "from": "broker",
      "to": "cloud_sub",
      "label": "分发温度",
      "style": "dashed",
      "direction": "event"
    },
    {
      "from": "sensor",
      "to": "broker",
      "label": "PUBLISH 湿度 (qos=1)",
      "style": "dashed",
      "direction": "request"
    },
    {
      "from": "broker",
      "to": "cloud_sub",
      "label": "分发湿度",
      "style": "dashed",
      "direction": "event"
    },
    {
      "from": "cloud_sub",
      "to": "broker",
      "label": "PUBLISH 告警 (qos=2)",
      "style": "dashed",
      "direction": "request"
    },
    {
      "from": "broker",
      "to": "phone_app",
      "label": "分发告警",
      "style": "dashed",
      "direction": "event"
    },
    {
      "from": "sensor",
      "to": "network_fail",
      "label": "TCP中断",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "network_fail",
      "to": "broker",
      "label": "心跳超时",
      "style": "dashed",
      "direction": "event"
    },
    {
      "from": "broker",
      "to": "cloud_sub",
      "label": "PUBLISH 遗嘱 (retain=true)",
      "style": "dashed",
      "direction": "event"
    }
  ],
  "regions": [
    {
      "id": "phase_i",
      "label": "连接建立 Phase I",
      "role": "传感器连接并设置遗嘱消息"
    },
    {
      "id": "phase_ii",
      "label": "正常运行 Phase II",
      "role": "周期数据上报与告警触发"
    },
    {
      "id": "phase_iii",
      "label": "断连处理 Phase III",
      "role": "心跳超时与遗嘱发布"
    }
  ],
  "callouts": [
    "遗嘱消息在连接建立时通过 will_set 设置，Broker 只在非正常断开时发布。",
    "QoS 2 告警保证精确一次送达，适用于关键通知场景。"
  ],
  "legend": [
    "实线箭头：连接建立（CONNECT/CONNACK）和确认",
    "蓝色虚线箭头：正常数据PUBLISH消息",
    "橙色虚线箭头：告警PUBLISH消息",
    "红色虚线箭头：遗嘱PUBLISH消息",
    "泳道：传感器(蓝色), Broker(灰色), 云订阅(深蓝色), 手机App(橙色)"
  ],
  "caption": "图9-5 展示了一个完整的MQTT智能家居监控交互序列。序列分三个阶段：Phase I连接建立与遗嘱设置，Phase II正常运行与告警触发，Phase III断连处理与遗嘱发布。重点突出QoS 1的周期数据、QoS 2的告警消息以及断连后的遗嘱消息三者的时序与角色差异。",
  "visual_constraints": [
    "最多6个组件，节点标签短，解释放入callouts。",
    "图例放在图底部，不遮挡分组边界。",
    "断连后的遗嘱发布用红色虚线强调。",
    "时间轴自上而下，标注Phase I/II/III分隔线。"
  ]
}
