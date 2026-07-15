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
  "id": "fig-1-1",
  "type": "timeline",
  "title": "图1-1 三次浪潮演进时间线示意",
  "purpose": "直观展示PC互联网、移动互联网、万物互联三个阶段的时间范围、连接主体、连接规模与核心驱动力",
  "audience_takeaway": "读者应理解三次浪潮演进时间线示意中的主链路、责任边界和工程取舍。",
  "visual_focus": "从从移动互联网到万物互联：实线箭头，标注'技术演进'的主链路。",
  "layout": "横向时间轴，从左到右排列三个阶段",
  "components": [
    {
      "id": "r1",
      "label": "从PC互联网",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "移动互联网：实线箭头，标注'技术演…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "从移动互联网",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r4",
      "label": "万物互联：实线箭头，标注'技术演进'",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "r3",
      "to": "r4",
      "label": "从移动互联网到万物互联：实线箭头…",
      "style": "solid",
      "direction": "request"
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
    "从PC互联网到移动互联网：实线箭头，标注'技术演进'",
    "从移动互联网到万物互联：实线箭头，标注'技术演进'"
  ],
  "legend": [
    "蓝色=第一次浪潮（PC互联网）",
    "橙色=第二次浪潮（移动互联网）",
    "绿色=第三次浪潮（万物互联）"
  ],
  "caption": "图1-1 三次浪潮演进时间线示意。时间轴下方标注连接规模数据，箭头表示演进方向。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
