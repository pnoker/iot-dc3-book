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
  "id": "fig-4-7",
  "type": "architecture",
  "title": "图4-7 智能路灯系统总体拓扑",
  "purpose": "展示混合使用NB-IoT和LoRa两种通信技术的路灯，如何通过统一接入层实现异构协议融合，使上层应用无感知。",
  "audience_takeaway": "读者应理解统一接入层如何将两套异构的物理链路抽象为一致的设备属性，业务层无需感知底层协议差异。",
  "visual_focus": "从应用层经统一接入层到两种路灯的主链路；设备影子作为中间抽象层使用绿色强调。",
  "layout": "三层结构：上为应用层（统一管控大屏+API网关），中为统一接入层（设备影子+NB-IoT驱动+LoRa驱动），下为感知层（NB-IoT路灯组+LoRa路灯组），层间蓝色实线条带表示数据流方向。",
  "components": [
    {
      "id": "app_layer",
      "label": "应用层",
      "type": "application",
      "subtitle": "统一管控大屏/API网关",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "device_shadow",
      "label": "设备影子",
      "type": "data",
      "subtitle": "switch/brightness/faultCode",
      "group": "access_domain",
      "priority": "primary",
      "shape": "database"
    },
    {
      "id": "driver_nbiot",
      "label": "NB-IoT驱动",
      "type": "platform",
      "subtitle": "LwM2M/CoAP",
      "group": "access_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "driver_lora",
      "label": "LoRa驱动",
      "type": "platform",
      "subtitle": "LoRaWAN 1.0.3",
      "group": "access_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "core_network",
      "label": "运营商核心网",
      "type": "external",
      "group": "nb_iot_path",
      "priority": "supporting",
      "shape": "boundary"
    },
    {
      "id": "enb",
      "label": "eNodeB基站",
      "type": "external",
      "group": "nb_iot_path",
      "priority": "normal",
      "shape": "boundary"
    },
    {
      "id": "nb_iot_lamp",
      "label": "NB-IoT路灯",
      "type": "edge",
      "subtitle": "1200盏(示意)",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "lora_ns",
      "label": "LoRa NS",
      "type": "external",
      "subtitle": "Network Server",
      "group": "lora_path",
      "priority": "supporting",
      "shape": "boundary"
    },
    {
      "id": "lora_gateway",
      "label": "LoRa网关",
      "type": "edge",
      "group": "lora_path",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "lora_lamp",
      "label": "LoRa路灯",
      "type": "edge",
      "subtitle": "800盏(示意)",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "app_layer",
      "to": "device_shadow",
      "label": "统一属性读写",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "device_shadow",
      "to": "driver_nbiot",
      "label": "指令路由",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "device_shadow",
      "to": "driver_lora",
      "label": "指令路由",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "driver_nbiot",
      "to": "core_network",
      "label": "CoAP报文",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "core_network",
      "to": "enb",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "enb",
      "to": "nb_iot_lamp",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "driver_lora",
      "to": "lora_ns",
      "label": "LoRaWAN帧",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "lora_ns",
      "to": "lora_gateway",
      "style": "dashed",
      "direction": "bottom-to-top"
    },
    {
      "from": "lora_gateway",
      "to": "lora_lamp",
      "style": "solid",
      "direction": "bottom-to-top"
    }
  ],
  "regions": [
    {
      "id": "access_domain",
      "label": "统一接入域",
      "role": "协议异构收敛、设备影子抽象、驱动调度边界"
    },
    {
      "id": "nb_iot_path",
      "label": "NB-IoT通信路径",
      "role": "授权频段、运营商核心网、LwM2M/CoAP链路"
    },
    {
      "id": "lora_path",
      "label": "LoRa通信路径",
      "role": "免授权频段、自建网关、LoRaWAN链路"
    }
  ],
  "callouts": [
    "统一接入层的价值在于：业务层只操作设备影子，不在意底层协议是LTE窄带还是LoRa扩频。",
    "设备影子是状态缓冲，掩盖不同协议的上报时延差异。",
    "新增设备类型只需开发驱动插件，业务层和前端界面完全不变。"
  ],
  "legend": [
    "蓝色（#4A90D9）：NB-IoT链路相关元素（驱动、核心网、基站、路灯）",
    "橙色（#E8913A）：LoRa链路相关元素（驱动、NS、网关、路灯）",
    "绿色（#7ED321）：统一接入层共享模块（设备影子、驱动管理背景）",
    "灰色（#F5F5F5）：应用层",
    "金色箭头（#F5A623）：主数据流",
    "实线箭头：强依赖链路；虚线箭头：可选或异步链路"
  ],
  "caption": "图4-7 智能路灯系统总体拓扑——展示混合使用NB-IoT和LoRa两种通信技术的路灯如何通过统一接入层实现异构协议融合，使上层应用无感知。",
  "visual_constraints": [
    "最多十个主节点，每个节点标签不超过14个字。",
    "设备影子节点使用绿色强调，驱动模块左右并排避免重叠。",
    "通信通路用折线连接，中间节点（核心网、eNodeB、LoRa NS、LoRa网关）使用细长框以节省空间。",
    "感知层路灯用阵列简图+文字标注数量（×1200 / ×800），不画2000个独立矩形。",
    "图例放在图中右下角空白区，不使用额外边框。"
  ]
}
