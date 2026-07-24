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
  "id": "fig-5-9",
  "type": "matrix",
  "title": "平台层工程检查矩阵",
  "purpose": "提供平台层设计时需关注的五个维度与四个检查属性，帮助工程师快速定位潜在风险",
  "audience_takeaway": "读者应理解平台层工程检查矩阵中的主链路、责任边界和工程取舍。",
  "visual_focus": "从进入下一判断到进入下一判断的主链路。",
  "layout": "5行 × 4列表格",
  "components": [
    {
      "id": "c1",
      "label": "进入下一判断",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "c2",
      "label": "进入下一判断",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "每个（行，列）交叉点放置一个关键检…",
      "style": "solid",
      "direction": "left-to-right"
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
    "每个（行，列）交叉点放置一个关键检查项，使用颜色图标表示风险等级：绿色✓（低风险）、黄色△（需关注）、红色✗（必须…"
  ],
  "legend": [
    "蓝色=核心平台/主链路；青绿色=设备与边缘；橙色=AI/风险/关键决策。"
  ],
  "caption": "图5-9 平台层工程检查矩阵。这些检查项来自多个企业级物联网项目设计阶段的复盘，帮助设计者在五个维度上快速定位风险点。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
