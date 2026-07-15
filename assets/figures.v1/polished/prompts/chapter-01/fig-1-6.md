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
  "id": "fig-1-6",
  "type": "layered",
  "title": "图1-6 四层物联网参考架构示意图",
  "purpose": "展示物联网四层参考架构及层间数据流",
  "audience_takeaway": "读者应理解物联网系统由四个职责清晰且相互依赖的层次构成，安全作为一个跨越所有层的约束条件存在。",
  "visual_focus": "数据从感知层上行至应用层的主链路，以及指令下行的反向回路。",
  "layout": "从下到上垂直堆叠，左侧标出贯穿的安全条带",
  "components": [
    {
      "id": "c1",
      "label": "应用层",
      "type": "application",
      "subtitle": "仪表盘、移动App、业务后端",
      "group": "application_domain",
      "priority": "primary",
      "shape": "process"
    },
    {
      "id": "c2",
      "label": "平台层",
      "type": "edge",
      "subtitle": "设备管理、数据存储与流处理、API网关",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "data"
    },
    {
      "id": "c3",
      "label": "网络层",
      "type": "platform",
      "subtitle": "MQTT、CoAP、LoRaWAN、NB-IoT",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "process"
    },
    {
      "id": "c4",
      "label": "感知层",
      "type": "edge",
      "subtitle": "传感器、执行器",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "data"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "感知层（传感器）→ 网络层：MQTT/CoAP——上行数据",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "网络层 → 平台层（API网关）——上行数据",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c3",
      "to": "c4",
      "label": "平台层（数据存储）→ 应用层（仪表盘）——推送数据",
      "style": "solid",
      "direction": "left-to-right"
    }
  ],
  "regions": [
    {
      "id": "application_domain",
      "label": "业务应用域",
      "role": "业务价值交付边界"
    },
    {
      "id": "edge_domain",
      "label": "设备与边缘域",
      "role": "现场异构资源边界"
    },
    {
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    }
  ],
  "callouts": [
    "感知层（传感器）→ 网络层：MQTT/CoAP——上行数据",
    "网络层 → 平台层（API网关）——上行数据",
    "平台层（数据存储）→ 应用层（仪表盘）——推送数据"
  ],
  "legend": [
    "橙色箭头：上行数据流",
    "蓝色箭头：下行指令流",
    "金色竖条：安全贯穿线"
  ],
  "caption": "图1-6 四层物联网参考架构。数据从感知层上行至应用层，指令以相反方向下行，形成闭环控制。安全条带从左侧贯穿，跨越所有层次。",
  "visual_constraints": [
    "垂直分层，每层用一个带标题的圆角矩形表示。上行数据用橙色箭头标注，下行指令用蓝色箭头标注。左侧绘制一条金色竖带，标注“安全”，表示安全是跨越所有层的治理能力。使用 SVG 绘制，整体居中对齐。"
  ]
}
