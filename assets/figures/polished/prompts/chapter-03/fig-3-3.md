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
  "id": "fig-3-3",
  "type": "layered",
  "title": "图3-3 RFID在智能仓储中的应用拓扑示意",
  "purpose": "展示UHF RFID在仓储场景中固定式门禁与手持终端配合使用的典型部署模式，帮助读者建立全局认识。",
  "audience_takeaway": "读者应理解RFID在智能仓储中的应用拓扑示意中的主链路、责任边界和工程取舍。",
  "visual_focus": "从RFID标签到终点的主链路。",
  "layout": "三层架构（云端层、边缘层、现场层），现场层再按功能分为入库区、出库区、货架区三个子区域。",
  "components": [
    {
      "id": "r1",
      "label": "RFID标签",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "固定式读写器A/B/手持终端：UH…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "固定式读写器A/B",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r4",
      "label": "RFID中间件：有线网络（RJ45…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r5",
      "label": "手持终端",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r6",
      "label": "RFID中间件：无线网络（Wi-F…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r7",
      "label": "RFID中间件",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r8",
      "label": "仓库管理系统（WMS/ERP）：A…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "r1",
      "to": "a_b_uhf",
      "label": "RFID标签 → 固定式读写器A/…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r3",
      "to": "rfid_rj45",
      "label": "固定式读写器A/B → RFID中…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r5",
      "to": "rfid_wi-fi",
      "label": "手持终端 → RFID中间件：无线…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r7",
      "to": "wms_erp_api",
      "label": "RFID中间件 → 仓库管理系统（…",
      "style": "dashed",
      "direction": "event"
    }
  ],
  "regions": [
    {
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    }
  ],
  "callouts": [
    "RFID标签 → 固定式读写器A/B/手持终端：UHF射频信号（读写器主动查询，标签回应），双向",
    "固定式读写器A/B → RFID中间件：有线网络（RJ45/工业以太网），单向数据上报",
    "手持终端 → RFID中间件：无线网络（Wi-Fi），单向数据上报"
  ],
  "legend": [
    "云端层：深蓝色背景；边缘层：浅灰色背景；现场层（入库区）：浅绿色背景；现场层（出库区）：浅蓝色背景；现场层（货架区）：浅黄色背景。",
    "有线连接：实线箭头；无线连接：虚线箭头。",
    "读写器元件：主机带天线图标；手持机元件：手持设备图标。"
  ],
  "caption": "图3-3 展示UHF RFID在仓储场景中固定式门禁与手持终端配合使用的典型部署模式。假设场景：固定式读写器在数秒内可读取约50-100个标签（取决于标签密度与天线安装角度）。不同区域用不同颜色标识。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
