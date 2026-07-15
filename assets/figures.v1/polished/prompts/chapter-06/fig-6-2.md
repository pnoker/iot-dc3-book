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
  "id": "fig-6-2",
  "type": "architecture",
  "title": "图6-2 物联网平台协议分层架构",
  "purpose": "展示MQTT、REST、gRPC在典型平台中的部署层次与交互主链路。",
  "audience_takeaway": "读者应理解设备、平台、北向三个层次的责任边界，以及各层次应选择的“最佳”协议。",
  "visual_focus": "从设备层经网关/边缘层到平台服务层再到北向应用层的主链路；不同协议用不同线型区分。",
  "layout": "自下而上四层：设备层、网关/边缘层、平台服务层、北向应用层。",
  "components": [
    {
      "id": "device",
      "label": "设备层",
      "type": "edge",
      "subtitle": "传感器、PLC、执行器",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "gateway",
      "label": "网关/边缘层",
      "type": "edge",
      "subtitle": "MQTT Broker、协议适配",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "mqtt_protocol",
      "label": "MQTT",
      "type": "platform",
      "subtitle": "发布/订阅、持续数据流",
      "group": "data_domain",
      "priority": "primary",
      "shape": "database"
    },
    {
      "id": "grpc_service",
      "label": "gRPC",
      "type": "platform",
      "subtitle": "服务间同步调用",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "rest_api",
      "label": "REST",
      "type": "platform",
      "subtitle": "北向API",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "device",
      "to": "gateway",
      "label": "设备数据上报",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "gateway",
      "to": "mqtt_protocol",
      "label": "持续数据流",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "mqtt_protocol",
      "to": "grpc_service",
      "label": "服务间调用",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "grpc_service",
      "to": "rest_api",
      "label": "数据提供",
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
      "id": "data_domain",
      "label": "数据资产域",
      "role": "数据传播与治理边界"
    },
    {
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    }
  ],
  "callouts": [
    "设备层→网关层：MQTT（发布/订阅）是主链路。",
    "网关层→平台层：MQTT用于持续数据流，少量REST用于配置更新。",
    "平台层内部：gRPC用于服务间同步调用。",
    "平台层→北向层：RESTful API为主，gRPC-Web为辅助场景。"
  ],
  "legend": [
    "蓝色=核心通信路径；青色=设备与边缘节点。",
    "实线箭头=主要通信链路；虚线箭头=辅助或可选的通信路径。"
  ],
  "caption": "图6-2 展示MQTT、REST、gRPC在物联网平台各层次中的部署位置与交互关系。",
  "visual_constraints": [
    "最多7个节点，节点标签短，解释放入callouts。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
