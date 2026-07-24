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
  "id": "fig-1-5",
  "type": "flowchart",
  "title": "图1-5 物联网价值迁移路径",
  "purpose": "展示物联网价值重心从连接层向智能决策层迁移的路径，以及每层对应的典型产品形态和商业模式。",
  "audience_takeaway": "读者应看到价值重心从左到右迁移，智能层的利润率和增长潜力显著高于连接层。",
  "visual_focus": "从左到右逐渐增粗的箭头表明价值占比变化；智能层节点用橙色强调。",
  "layout": "水平流向，三个主节点从左到右排列，下方通过虚线连接商业模式标签。",
  "components": [
    {
      "id": "connectivity_layer",
      "label": "连接层",
      "type": "platform",
      "subtitle": "模组、SIM、连接管理",
      "group": "low_value_region",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "platform_layer",
      "label": "平台层",
      "type": "platform",
      "subtitle": "设备管理、规则引擎",
      "group": "mid_value_region",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "intelligence_layer",
      "label": "智能层",
      "type": "ai",
      "subtitle": "数据分析、AI决策",
      "group": "high_value_region",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "connectivity_business",
      "label": "按连接计费",
      "type": "application",
      "subtitle": "低毛利",
      "group": "low_value_region",
      "priority": "normal",
      "shape": "decision"
    },
    {
      "id": "platform_business",
      "label": "按设备/消息计费",
      "type": "application",
      "subtitle": "中等毛利",
      "group": "mid_value_region",
      "priority": "normal",
      "shape": "decision"
    },
    {
      "id": "intelligence_business",
      "label": "按决策/效果计费",
      "type": "application",
      "subtitle": "高毛利",
      "group": "high_value_region",
      "priority": "primary",
      "shape": "decision"
    }
  ],
  "connections": [
    {
      "from": "connectivity_layer",
      "to": "platform_layer",
      "label": "价值汇聚",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "platform_layer",
      "to": "intelligence_layer",
      "label": "数据驱动",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "connectivity_layer",
      "to": "connectivity_business",
      "label": "对应",
      "style": "dashed",
      "direction": "request"
    },
    {
      "from": "platform_layer",
      "to": "platform_business",
      "label": "对应",
      "style": "dashed",
      "direction": "request"
    },
    {
      "from": "intelligence_layer",
      "to": "intelligence_business",
      "label": "对应",
      "style": "dashed",
      "direction": "request"
    }
  ],
  "regions": [
    {
      "id": "low_value_region",
      "label": "低价值区",
      "role": "连接已被商品化，利润薄。"
    },
    {
      "id": "mid_value_region",
      "label": "中价值区",
      "role": "平台层由巨头主导，独立厂商空间有限。"
    },
    {
      "id": "high_value_region",
      "label": "高价值区",
      "role": "智能层由数据分析和AI驱动，利润率最高。"
    }
  ],
  "callouts": [
    "箭头宽度示意价值占比：连接层最细，智能层最粗。",
    "智能层的利润率远高于连接层，这是产业竞相迁移的原因。"
  ],
  "legend": [
    "蓝色方框 = 平台/连接服务；橙色方框 = AI/智能；虚线 = 商业模式映射。",
    "实线箭头 = 价值流向；宽度代表相对价值占比。"
  ],
  "caption": "图1-5 物联网产业价值重心从连接层向平台层、最终向智能决策层迁移的路径。",
  "visual_constraints": [
    "三个主节点水平排列，间距均匀。",
    "商业模式标签与主节点用虚线连接，宽度不超过主节点。",
    "箭头宽度体现相对价值，不可夸张。"
  ]
}
