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
  "id": "fig-4-5",
  "type": "dataflow",
  "title": "图4-5 设备抽象与物模型映射示意图",
  "purpose": "展示从底层原生数据（Modbus寄存器、BLE特征值、LoRaWAN负载）到统一物模型实例的映射过程，说明设备抽象层如何屏蔽协议差异，实现数据模型标准化。",
  "audience_takeaway": "读者应理解设备抽象与物模型映射示意图中的主链路、责任边界和工程取舍。",
  "visual_focus": "从Modbus 寄存器值到数据映射层 : 解析值的主链路。",
  "layout": "从左至右三列流向：原生数据→驱动解析→数据映射层→物模型实例→平台消费方",
  "components": [
    {
      "id": "r1",
      "label": "Modbus 寄存器值",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "Modbus Driver : 原…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "Modbus Driver",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r4",
      "label": "数据映射层 : 解析值",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "r5",
      "label": "BLE 特征值",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r6",
      "label": "BLE Driver : 原始帧",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r7",
      "label": "BLE Driver",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r8",
      "label": "LoRaWAN 负载",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r9",
      "label": "LoRaWAN Driver…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r10",
      "label": "LoRaWAN Driver",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "r1",
      "to": "modbus_driver",
      "label": "Modbus 寄存器值 → Mod…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r3",
      "to": "r4",
      "label": "整型",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r5",
      "to": "r6",
      "label": "BLE 特征值 → BLE Dri…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r7",
      "to": "r4",
      "label": "浮点",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r8",
      "to": "lorawan_driver",
      "label": "LoRaWAN 负载 → LoRa…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r10",
      "to": "r4",
      "label": "十六进制解码",
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
      "id": "data_domain",
      "label": "数据资产域",
      "role": "数据沉淀与治理边界"
    }
  ],
  "callouts": [
    "Modbus 寄存器值 → Modbus Driver : 原始帧",
    "Modbus Driver → 数据映射层 : 解析值（整型）",
    "BLE 特征值 → BLE Driver : 原始帧"
  ],
  "legend": [
    "蓝色方块：原生数据源",
    "青绿色方块：协议驱动",
    "橙色方块：数据映射层（核心抽象）",
    "绿色方块：统一物模型实例",
    "灰色方块：平台应用",
    "实线箭头：数据流动方向，标注数据转换/传输步骤"
  ],
  "caption": "图4-5 三种协议传感器数据经过驱动解析和数据映射层，统一转换为相同结构的物模型实例，上层应用消费时无需感知底层协议的差异",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
