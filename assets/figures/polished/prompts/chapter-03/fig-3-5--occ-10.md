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
  "id": "fig-3-5",
  "type": "layered",
  "title": "边缘计算节点典型部署架构",
  "purpose": "说明边缘计算节点在物联网系统中的三层部署逻辑与数据流向",
  "audience_takeaway": "读者应理解边缘计算节点典型部署架构中的主链路、责任边界和工程取舍。",
  "visual_focus": "从第1层 传感器端（靠近被监测对象）到第1层 传感器端（靠近被监测对象）的主链路。",
  "layout": "layered",
  "components": [
    {
      "id": "layer_1",
      "label": "第1层 传感器端（靠近被监测对象）",
      "type": "edge",
      "subtitle": "传感器接Cortex-M4级MCU，执行A/D转换、滑…",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "layer_2",
      "label": "第2层 边缘网关（靠近汇聚点）",
      "type": "edge",
      "subtitle": "网关接收多条传感器链路的处理后数据，执行协议转换（格式…",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "layer_3",
      "label": "第3层 云平台（远程管理与模型训练）",
      "type": "edge",
      "subtitle": "云侧使用全量历史数据训练模型，下发至边缘网关；同时接收…",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "layer_1",
      "to": "layer_2",
      "label": "特征值/事件",
      "style": "dashed",
      "direction": "event"
    },
    {
      "from": "layer_2",
      "to": "layer_3",
      "label": "聚合值/异常告警",
      "style": "risk",
      "direction": "event"
    },
    {
      "from": "layer_3",
      "to": "layer_2",
      "label": "训练后模型/阈值",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "layer_2",
      "to": "layer_1",
      "label": "参数调整/唤醒指令",
      "style": "solid",
      "direction": "request"
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
    "第1层 传感器端 → 第2层 边缘网关（特征值/事件）",
    "第2层 边缘网关 → 第3层 云平台（聚合值/异常告警）",
    "第3层 云平台 → 第2层 边缘网关（训练后模型/阈值）"
  ],
  "legend": [
    "已处理数据或压缩数据上传方向",
    "模型参数、阈值或配置下发方向"
  ],
  "caption": "边缘计算节点典型部署架构。物理世界中各类传感器靠近被监测对象布放，附接MCU级节点完成首级处理（采样、滤波、阈值判断）；这些节点通过短距或长距无线链路（BLE、LoRa、RS-485）连接至边缘网关，网关汇聚数据后由应用处理器级节点执行协议转换与通道融合；网关再与云端IoT平台（如IoT DC3）进行双向数据同步。云侧承担模型训练和高阶分析任务，推理结果可沿相同路径下发给现场，形成完整闭环。架构图中包含了从端侧到云侧的三层结构及其数据流方向。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
