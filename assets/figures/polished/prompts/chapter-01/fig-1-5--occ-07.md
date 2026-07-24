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
  "title": "图1-5 物联网平台市场格局示意",
  "purpose": "示意展示2020年前后主流物联网云平台在生态完整性与运营商支持力度两个维度的分布，帮助读者理解平台选择的工程权衡。",
  "audience_takeaway": "读者应理解平台市场并非一家独大，差异化定位决定了不同场景下的选型优先级。",
  "visual_focus": "主云平台在生态完整性维度靠近左边界，运营商平台在运营商支持力度维度突出。",
  "layout": "二维气泡图：横轴为生态完整性（低→高），纵轴为运营商支持力度（弱→强），气泡大小示意市场影响力（示意数据，不反映真实份额）。",
  "components": [
    {
      "id": "platform_a",
      "label": "平台A",
      "type": "platform",
      "subtitle": "云原生厂商",
      "group": "dominant_region",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "platform_b",
      "label": "平台B",
      "type": "platform",
      "subtitle": "运营商平台",
      "group": "dominant_region",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "platform_c",
      "label": "平台C",
      "type": "platform",
      "subtitle": "开源或行业平台",
      "group": "niche_region",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "platform_d",
      "label": "平台D",
      "type": "platform",
      "subtitle": "垂直行业方案",
      "group": "niche_region",
      "priority": "supporting",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "platform_a",
      "to": "platform_b",
      "label": "气泡位置仅用于示意差异化，不代表精确市场份额",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "platform_b",
      "to": "platform_c",
      "label": "气泡位置仅用于示意差异化，不代表精确市场份额",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "platform_c",
      "to": "platform_d",
      "label": "气泡位置仅用于示意差异化，不代表精确市场份额",
      "style": "solid",
      "direction": "left-to-right"
    }
  ],
  "regions": [
    {
      "id": "dominant_region",
      "label": "主导区",
      "role": "生态完整且运营商支持强的市场定位"
    },
    {
      "id": "niche_region",
      "label": "细分区",
      "role": "生态有限但运营商支持强的垂直场景定位"
    }
  ],
  "callouts": [
    "气泡大小示意市场影响力，但本图仅为示意，不反映真实份额。",
    "平台选型的首要权衡：生态完整性与运营商支持力度往往不可兼得。"
  ],
  "legend": [
    "蓝色=云原生平台；青绿色=运营商平台；灰色=开源或垂直方案。",
    "气泡大小示意市场影响力（非真实数据）。"
  ],
  "caption": "图1-5 示意展示2020年前后物联网平台市场在生态完整性与运营商支持力度两个维度的差异化定位。气泡位置与大小仅为教学示意，不代表真实市场份额。",
  "visual_constraints": [
    "气泡最多四个，标签简短，不遮挡坐标轴。",
    "横纵坐标刻度清晰，图注说明示意性质。"
  ]
}
