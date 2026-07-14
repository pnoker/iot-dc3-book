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
  "id": "fig-1-2",
  "type": "architecture",
  "title": "图1-2 PC互联网时代连接架构",
  "purpose": "展示PC互联网时代用户—PC—万维网—信息的连接链路， 突出物设备尚未纳入联网范围，为后续物联网连接范式对比做铺垫。",
  "audience_takeaway": "展示PC互联网时代用户—PC—万维网—信息的连接链路， 突出物设备尚未纳入联网范围，为后续物联网连接范式对比做铺垫。",
  "visual_focus": "从左至右分四层排列：\n- 最左侧为“用户”图标\n- 中间靠左为“桌面PC”（含浏览器）\n- 核心为“万维网”云团\n- 右侧为“信息内容”页图标\n底层从PC至信息内容标注“TCP/IP协议族”大矩形\n右下角用浅橙色虚线框标注“物（未连接）”区域，框内放置传感器图标与执行器图标",
  "layout": "从左至右分四层排列：\n- 最左侧为“用户”图标\n- 中间靠左为“桌面PC”（含浏览器）\n- 核心为“万维网”云团\n- 右侧为“信息内容”页图标\n底层从PC至信息内容标注“TCP/IP协议族”大矩形\n右下角用浅橙色虚线框标注“物（未连接）”区域，框内放置传感器图标与执行器图标",
  "components": [
    {
      "id": "c1",
      "label": "用户",
      "type": "application",
      "subtitle": "一个抽象人体图标",
      "group": "application_domain",
      "priority": "primary",
      "shape": "process"
    },
    {
      "id": "c2",
      "label": "桌面PC",
      "type": "platform",
      "subtitle": "台式机图标，内部标注浏览器图标与文字‘’",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "process"
    },
    {
      "id": "c3",
      "label": "万维网",
      "type": "platform",
      "subtitle": "一个灰色半透明圆形云，标注‘’",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "process"
    },
    {
      "id": "c4",
      "label": "信息内容",
      "type": "platform",
      "subtitle": "多个白色小矩形叠放，代表不同网页",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "process"
    },
    {
      "id": "c5",
      "label": "TCP/IP协议族",
      "type": "platform",
      "subtitle": "位于底层的大矩形，使用蓝色系渐变，覆盖整个架构范围",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "process"
    },
    {
      "id": "c6",
      "label": "搜索引擎/门户",
      "type": "platform",
      "subtitle": "在万维网与信息内容之间标注一个竖框",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "process"
    },
    {
      "id": "c7",
      "label": "物（未连接）",
      "type": "edge",
      "subtitle": "一个浅橙色虚线框，位于右下角，框内放置传感器图标与执行器图标",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "data"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "用户 → 桌面PC（实线箭头，用户操作）",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "桌面PC → 万维网（实线箭头，HTTP请求）",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c3",
      "to": "c4",
      "label": "万维网 → 信息内容（实线箭头，检索返回）",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c4",
      "to": "c5",
      "label": "搜索引擎/门户置于万维网与信息内容之间",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c5",
      "to": "c6",
      "label": "物（未连接）与系统之间画断开线，表示无连接",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c6",
      "to": "c7",
      "label": "用户 → 桌面PC（实线箭头，用户操作）",
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
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    },
    {
      "id": "edge_domain",
      "label": "设备与边缘域",
      "role": "现场异构资源边界"
    }
  ],
  "callouts": [
    "用户 → 桌面PC（实线箭头，用户操作）",
    "桌面PC → 万维网（实线箭头，HTTP请求）",
    "万维网 → 信息内容（实线箭头，检索返回）"
  ],
  "legend": [
    "→（实线单箭头）：数据请求/响应路径",
    "— —（虚线）：表示尚未连接的物理世界",
    "浅橙色填充：待纳入联网范围的区域标签"
  ],
  "caption": "主架构展现“用户—桌面PC（浏览器）—万维网—信息内容”四层关系。底层为TCP/IP协议族，提供通信基础。\n右下角用浅橙色虚线框标注传感器、执行器，用断开线强调它们尚未接入互联网。这与当今物联网场景形成鲜明对比——\n在物联网中，这些物设备通过感知层和网络层成为体系的一部分（见第2章和第3章）。",
  "visual_constraints": [
    "SVG绘制。TCP/IP区域用蓝色系渐变矩形，万维网用浅灰色带阴影的圆形，网页用白色小矩形叠放。\n箭头使用<path>线宽2px，末端带三角形。虚线框stroke-dasharray=5,5，浅橙色填充。中文标注字号不小于14px。"
  ]
}
