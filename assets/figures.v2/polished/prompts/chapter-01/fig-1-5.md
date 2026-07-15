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
  "id": "fig-1-5",
  "type": "architecture",
  "title": "图1-5 物联网系统五要素关系示意",
  "purpose": "直观展示感知、传输、处理、应用、安全五大要素的层次关系、数据流向与控制流，让读者快速建立物联网系统整体架构认知。",
  "audience_takeaway": "读者应理解五要素之间的关系：数据从感知层经传输层到处理层和应用层，控制指令反向流动，安全机制贯穿全程。",
  "visual_focus": "主链路从感知层起，经传输层到处理层，再到应用层；虚线表示控制指令逆向路径；安全层以贯穿式长条表示。",
  "layout": "水平分层架构图，顶层从左至右依次为感知→传输→处理→应用四个模块串联，安全层作为一个贯穿底部的横向长条矩形，垂直覆盖上方四个模块。",
  "components": [
    {
      "id": "c1",
      "label": "感知层（最左蓝色节点）",
      "type": "edge",
      "subtitle": "传感器与执行器，标注'S'和'A'图标",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "data"
    },
    {
      "id": "c2",
      "label": "传输层（左中蓝色节点）",
      "type": "platform",
      "subtitle": "协议汇聚，列出Wi-Fi、LoRa、BLE三种代表性协议",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "process"
    },
    {
      "id": "c3",
      "label": "处理层（右中橙色节点）",
      "type": "edge",
      "subtitle": "平台与边缘，标注规则引擎与时序库",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "process"
    },
    {
      "id": "c4",
      "label": "应用层（最右紫色节点）",
      "type": "security",
      "subtitle": "人机界面，标注手机、大屏、告警",
      "group": "governance_domain",
      "priority": "normal",
      "shape": "process"
    },
    {
      "id": "c5",
      "label": "安全层（底部灰色虚线矩形框）",
      "type": "security",
      "subtitle": "纵向贯穿，标注认证、加密、审计",
      "group": "governance_domain",
      "priority": "normal",
      "shape": "process"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "感知层→传输层：传感器数据上报，实线箭头带标注'数据上传'",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "传输层→处理层：数据转发，实线箭头",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c3",
      "to": "c4",
      "label": "处理层→应用层：分析结果推送与告警，实线箭头",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c4",
      "to": "c5",
      "label": "应用层→传输层→感知层：控制指令下发路径（逆向），虚线箭头…",
      "style": "dashed",
      "direction": "left-to-right"
    }
  ],
  "regions": [
    {
      "id": "edge_domain",
      "label": "设备与边缘域",
      "role": "现场异构资源边界"
    },
    {
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    },
    {
      "id": "governance_domain",
      "label": "治理与安全域",
      "role": "风险控制与责任边界"
    }
  ],
  "callouts": [
    "感知层→传输层：传感器数据上报，实线箭头带标注'数据上传'。",
    "传输层→处理层：数据转发，实线箭头。",
    "处理层→应用层：分析结果推送与告警，实线箭头。"
  ],
  "legend": [
    "蓝色=感知与传输；橙色=处理；紫色=应用；灰色虚线矩形=安全贯穿层",
    "实线箭头=数据上报；虚线箭头=控制指令下发；底部标注短线=安全通道"
  ],
  "caption": "图1-5 物联网系统五要素关系示意",
  "visual_constraints": [
    "SVG渲染，宽高比16:5。顶层四模块横向等距排列，间距18%。安全层高度为顶层模块高度40%，完全覆盖底层。采用圆角矩形（r=6px），线宽2px（虚线间隔6px）。配色：感知/传输用#2563EB主蓝，处理用#F97316橙，应用用#8B5CF6紫，安全层用#E2E8F0背景加#94A3B8虚线边框。图标用简单矢量符号，字号：模块中文16px，图例10px。"
  ]
}
