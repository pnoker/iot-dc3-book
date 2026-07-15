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
  "id": "fig-6-3",
  "type": "architecture",
  "title": "图6-3 智能楼宇物联网系统微服务参考架构（示意）",
  "purpose": "展示按DDD限界上下文拆分的智能楼宇微服务分层架构，以及数据流与控制流的分离路径。",
  "audience_takeaway": "读者应理解智能楼宇物联网系统微服务参考架构（示意）中的主链路、责任边界和工程取舍。",
  "visual_focus": "从起点到对应的协议驱动层服务，实线箭头的主链路。",
  "layout": "自下而上分层：南向设备层 -> 协议驱动层 -> 云端微服务层 -> 北向接入与展示层。",
  "components": [
    {
      "id": "c1",
      "label": "南向设备层",
      "type": "edge",
      "subtitle": "MQTT传感器、Modbus控制器、BACnet空调系统，使用青绿色设备节点",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "data"
    },
    {
      "id": "c2",
      "label": "协议驱动层（边缘网关）",
      "type": "edge",
      "subtitle": "MQTT驱动、Modbus驱动、BACnet驱动，使用青绿色服务块",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "process"
    },
    {
      "id": "c3",
      "label": "云端微服务层",
      "type": "edge",
      "subtitle": "设备管理服务、数据采集服务、告警引擎服务、能源分析服务、用户与租户服务，均使用蓝色…",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "process"
    },
    {
      "id": "c4",
      "label": "北向接入与展示层",
      "type": "edge",
      "subtitle": "API网关（橙色网关节点），管理控制台（绿色前端节点）",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "data"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "南向设备经由MQTT/Modbus/BACnet协议接入对…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "协议驱动层服务通过消息队列将标准化报文发送至云端的数据采集…",
      "style": "dashed",
      "direction": "left-to-right"
    },
    {
      "from": "c3",
      "to": "c4",
      "label": "数据采集服务通过消息队列将实时数据推送至告警引擎服务，虚线…",
      "style": "dashed",
      "direction": "left-to-right"
    }
  ],
  "regions": [
    {
      "id": "edge_domain",
      "label": "设备与边缘域",
      "role": "现场异构资源边界"
    }
  ],
  "callouts": [
    "南向设备经由MQTT/Modbus/BACnet协议接入对应的协议驱动层服务，实线箭头。",
    "协议驱动层服务通过消息队列将标准化报文发送至云端的数据采集服务，虚线箭头。",
    "数据采集服务通过消息队列将实时数据推送至告警引擎服务，虚线箭头。"
  ],
  "legend": [
    "青色=南向设备与边缘接入；绿色=云端领域服务。",
    "紫色=数据存储；橙色=API/展示入口；虚线=异步消息。"
  ],
  "caption": "图6-3 展示智能楼宇物联网系统按 DDD 限界上下文拆分后的微服务参考架构，突出协议驱动、领域服务和数据路径的分离。",
  "visual_constraints": [
    "使用 architecture-diagram 暗色出版风格绘制，按南向设备、边缘驱动、云端微服务、北向入口自下而上分层，节点短标签，箭头标注同步/异步链路。"
  ]
}
