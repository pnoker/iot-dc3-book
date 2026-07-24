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
  "id": "fig-9-7",
  "type": "matrix",
  "title": "HTTP、MQTT、CoAP应用层协议角色对比",
  "purpose": "直观展示HTTP、MQTT和CoAP在物联网通信架构中的定位差异——传输层、通信模型和典型场景——帮助工程师在协议选型时快速决策。",
  "audience_takeaway": "读者应理解HTTP、MQTT、CoAP应用层协议角色对比中的主链路、责任边界和工程取舍。",
  "visual_focus": "从TCP + TLS到请求/响应 + Observe的主链路。",
  "layout": "三列水平排列，每列自顶向下分为三层“典型场景 → 通信模型 → 传输层”。三层之间用浅灰隔线分隔。 - 左列（HTTP）： - 顶层（典型场景/浅蓝矩形块）：“设备配网”、“网关北向” - 中层（通信模型/浅绿矩形块）：“请求/响应” - 底层（传输层/浅黄矩形块）：“TCP + TLS” - 中列（MQTT）： - 顶层（典型场景/浅蓝矩形块）：“远程监控”、“双向指令” - 中层（通信模型/浅绿矩形块）：“发布/订阅（Broker中转）” - 底层（传输层/浅黄矩形块）：“TCP” - 右列（CoAP）： - 顶层（典型场景/浅蓝矩形块）：“传感器采集”、“状态上报” - 中层（通信模型/浅绿矩形块）：“请求/响应 + Observe” - 底层（传输层/浅黄矩形块）：“UDP + DTLS”",
  "components": [
    {
      "id": "http_scenario",
      "label": "设备配网 / 网关北向",
      "type": "application",
      "subtitle": "HTTP · 典型场景",
      "group": "protocol_http",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "mqtt_scenario",
      "label": "远程监控 / 双向指令",
      "type": "application",
      "subtitle": "MQTT · 典型场景",
      "group": "protocol_mqtt",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "coap_scenario",
      "label": "传感器采集 / 状态上报",
      "type": "application",
      "subtitle": "CoAP · 典型场景",
      "group": "protocol_coap",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "http_model",
      "label": "请求/响应",
      "type": "platform",
      "subtitle": "HTTP · 通信模型",
      "group": "protocol_http",
      "priority": "normal",
      "shape": "bus"
    },
    {
      "id": "mqtt_model",
      "label": "发布/订阅（Broker中转）",
      "type": "platform",
      "subtitle": "MQTT · 通信模型",
      "group": "protocol_mqtt",
      "priority": "primary",
      "shape": "bus"
    },
    {
      "id": "coap_model",
      "label": "请求/响应 + Observe",
      "type": "platform",
      "subtitle": "CoAP · 通信模型",
      "group": "protocol_coap",
      "priority": "normal",
      "shape": "bus"
    },
    {
      "id": "http_transport",
      "label": "TCP + TLS",
      "type": "edge",
      "subtitle": "HTTP · 传输层",
      "group": "protocol_http",
      "priority": "normal",
      "shape": "bus"
    },
    {
      "id": "mqtt_transport",
      "label": "TCP",
      "type": "edge",
      "subtitle": "MQTT · 传输层",
      "group": "protocol_mqtt",
      "priority": "normal",
      "shape": "bus"
    },
    {
      "id": "coap_transport",
      "label": "UDP + DTLS",
      "type": "edge",
      "subtitle": "CoAP · 传输层",
      "group": "protocol_coap",
      "priority": "normal",
      "shape": "bus"
    }
  ],
  "connections": [
    {
      "from": "http_transport",
      "to": "http_model",
      "label": "承载",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "http_model",
      "to": "http_scenario",
      "label": "适用",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "mqtt_transport",
      "to": "mqtt_model",
      "label": "承载",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "mqtt_model",
      "to": "mqtt_scenario",
      "label": "适用",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "coap_transport",
      "to": "coap_model",
      "label": "承载",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "coap_model",
      "to": "coap_scenario",
      "label": "适用",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "mqtt_model",
      "to": "http_model",
      "label": "Broker 中转",
      "style": "dashed",
      "direction": "event"
    },
    {
      "from": "mqtt_model",
      "to": "coap_model",
      "label": "Broker 中转",
      "style": "dashed",
      "direction": "event"
    }
  ],
  "regions": [
    {
      "id": "protocol_http",
      "label": "HTTP",
      "role": "Web API 与网关北向通信"
    },
    {
      "id": "protocol_mqtt",
      "label": "MQTT",
      "role": "Broker 中转与双向消息"
    },
    {
      "id": "protocol_coap",
      "label": "CoAP",
      "role": "受限设备低功耗通信"
    }
  ],
  "callouts": [
    "从中列MQTT的中层“发布/订阅”层，灰色虚线箭头向左/向右分别指向左列和右列底部的设备图标，表示消息流经Brok…",
    "左右两列中，黑色箭头从“传输层”向上指向“场景”层，表示设备与服务器直接点对点通信"
  ],
  "legend": [
    "浅蓝矩形块：典型场景",
    "浅绿矩形块：通信模型",
    "浅黄矩形块：传输层",
    "灰色虚线箭头：经Broker中转的消息流",
    "黑色箭头：直接点对点通信",
    "底端图标+符号：设备供电特征（AC供电/电池供电/能量采集）"
  ],
  "caption": "HTTP适合设备配网、平台API和网关北向通信，因为它利用现有Web基础设施，调试方便、安全成熟。MQTT和CoAP面向受限设备：MQTT擅长双向消息与大规模管理，CoAP聚焦最小功耗和单对单通信。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
