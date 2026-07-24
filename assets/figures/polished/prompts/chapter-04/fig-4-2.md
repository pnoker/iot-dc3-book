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
  "id": "fig-4-2",
  "type": "layered",
  "title": "图4-2 统一接入层的逻辑定位与内部能力分层",
  "purpose": "展示统一接入层在物联网平台中的位置，以及其内部的能力层分解，帮助读者理解这一层如何'夹在'异构协议与统一业务服务之间，逐层完成数据加工。",
  "audience_takeaway": "读者应理解统一接入层的逻辑定位——它不是一个单一服务，而是由协议转换、设备模型映射、安全认证三个子层组成的中间层。",
  "visual_focus": "从底层异构设备开始，经过三个子层依次向上，最终输出标准化事件/属性到业务层的主链路。",
  "layout": "竖向堆叠，层之间用实线分隔，子层用虚线分隔。所有层宽度一致。",
  "components": [
    {
      "id": "device_layer",
      "label": "异构设备与协议",
      "type": "edge",
      "subtitle": "Modbus/MQTT/LoRaWAN/BLE/NB-IoT",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "protocol_adapt",
      "label": "协议转换与适配",
      "type": "platform",
      "subtitle": "连接管理·报文解析·格式归一",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "thing_model",
      "label": "统一设备模型",
      "type": "platform",
      "subtitle": "位号→属性/事件/服务映射",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "security_auth",
      "label": "安全与认证",
      "type": "security",
      "subtitle": "身份校验·TLS终结·密钥协商",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "app_service",
      "label": "应用层业务服务",
      "type": "application",
      "subtitle": "告警·分析·可视化",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "device_layer",
      "to": "protocol_adapt",
      "label": "原始报文",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "protocol_adapt",
      "to": "thing_model",
      "label": "结构化键值",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "thing_model",
      "to": "security_auth",
      "label": "物模型实例",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "security_auth",
      "to": "app_service",
      "label": "可信属性/事件",
      "style": "solid",
      "direction": "bottom-to-top"
    }
  ],
  "regions": [],
  "callouts": [
    "统一接入层的三个子层是逻辑上的顺序处理，实际实现中每个子层可能由独立的微服务或SDK组件完成。",
    "协议转换与适配层是接入层中最容易随设备种类增加而膨胀的组件，需要严格隔离每个协议的驱动。"
  ],
  "legend": [
    "底层：浅绿色，表示物理世界。",
    "中层：浅灰色，内部的三个子层用浅蓝、浅青、浅橙区分，分别对应协议适配、模型映射、安全认证。",
    "顶层：浅蓝色，表示数字世界业务服务。",
    "箭头自下而上，表示数据从设备到业务的流动方向。"
  ],
  "caption": "图4-2 统一接入层的逻辑定位与内部能力分层，明确了从异构协议到标准化业务事件的三层加工路径。",
  "visual_constraints": [
    "最多6个主节点，每个节点标签不超过16个汉字。",
    "子层之间用虚线分隔，不与层间实线混淆。",
    "箭头使用蓝色实线，方向明确自下而上。"
  ]
}
