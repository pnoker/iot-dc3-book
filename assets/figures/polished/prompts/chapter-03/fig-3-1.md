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
  "id": "fig-3-1",
  "type": "layered",
  "title": "图3-1 感知层在物联网多层参考架构中的位置",
  "purpose": "展示感知层在物联网参考架构中的底层位置，及其内部三大类组件（传感器、识别设备、定位模块）与上层网络层/平台层/应用层的接口关系。同时标注感知层的核心能力集合与逻辑边界。",
  "audience_takeaway": "读者应理解感知层在物联网多层参考架构中的位置中的主链路、责任边界和工程取舍。",
  "visual_focus": "从网络层到终点的主链路。",
  "layout": "自下而上分层架构：物理世界→感知层→网络层→平台层→应用层。感知层内部三等分展示传感器、识别设备、定位模块。平台层内部四等分展示设备管理、物模型管理、数据存储、规则引擎。",
  "components": [
    {
      "id": "r1",
      "label": "物理世界",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "感知层：向下箭头，标签'物理量 /…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "感知层",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r4",
      "label": "网络层：向下箭头，标签'位号值流…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r5",
      "label": "网络层",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r6",
      "label": "平台层：向下箭头，标签'传输协议…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r7",
      "label": "平台层",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r8",
      "label": "应用层：向下箭头，标签'API 与…",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "r9",
      "label": "应用层",
      "type": "application",
      "group": "application_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r10",
      "label": "物理世界：向上虚线箭头，标签'控制…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "r5",
      "to": "mqt",
      "label": "网络层→平台层：向下箭头，标签'传…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r7",
      "to": "api",
      "label": "平台层→应用层：向下箭头，标签'A…",
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
    },
    {
      "id": "application_domain",
      "label": "业务应用域",
      "role": "业务价值交付边界"
    }
  ],
  "callouts": [
    "物理世界→感知层：向下箭头，标签'物理量 / 状态'",
    "感知层→网络层：向下箭头，标签'位号值流 / 身份码 / 坐标'",
    "网络层→平台层：向下箭头，标签'传输协议 (MQTT/Modbus/OPC UA)'"
  ],
  "legend": [
    "蓝色系（#2C5F8A/#3D70B0）= 感知层及其组件",
    "蓝绿色（#3A7CA5）= 网络层",
    "绿色系（#6BBF59/#7DCE82）= 平台层",
    "橙色（#F3A712）= 应用层",
    "灰色（#AAB7B8）= 物理世界",
    "实线箭头 = 数据流，虚线箭头 = 控制流"
  ],
  "caption": "图3-1 感知层在物联网多层参考架构中的位置。感知层包含传感器、识别设备和定位模块三大组件，负责将物理世界信息转换为位号值流、身份码和坐标数据，通过网络层上传至平台层和应用层。箭头方向表示数据流向（自下而上）或控制指令流向（自上而下虚线）。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
