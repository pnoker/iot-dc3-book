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
  "id": "fig-11-5",
  "type": "flowchart",
  "title": "图11-5 智慧交通系统集成部署工程检查流程",
  "purpose": "展示四个检查域在部署流程中的依赖关系与先后顺序，帮助工程师规划执行步骤和风险节点",
  "audience_takeaway": "读者应理解智慧交通系统集成部署工程检查流程中的主链路、责任边界和工程取舍。",
  "visual_focus": "从泳道4两个决策节点顺序通过后到达终点部署上线的主链路。",
  "layout": "横向泳道图，四条水平泳道，从上到下排布；泳道之间用带箭头的流程线连接",
  "components": [
    {
      "id": "r1",
      "label": "泳道4两个决策节点顺序通过后",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "primary",
      "shape": "decision"
    },
    {
      "id": "r2",
      "label": "达终点部署上线",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "r1",
      "to": "r2",
      "label": "泳道4两个决策节点顺序通过后，到达…",
      "style": "solid",
      "direction": "request"
    }
  ],
  "regions": [
    {
      "id": "intelligence_domain",
      "label": "智能决策域",
      "role": "模型、规则与 Agent 边界"
    },
    {
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    }
  ],
  "callouts": [
    "泳道1三个决策节点顺序通过后，进入泳道2",
    "泳道2三个决策节点顺序通过后，进入泳道3",
    "泳道3两个决策节点顺序通过后，进入泳道4"
  ],
  "legend": [
    "绿色菱形：检查项通过",
    "红色菱形：检查项未通过，需返回上一步调整",
    "蓝色圆角矩形：操作节点或最终状态",
    "实线箭头：流程方向",
    "虚线箭头：返回修正路径（未通过）"
  ],
  "caption": "图11-5 智慧交通系统集成部署工程检查流程",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "决策节点必须写成可判断的问题或动作，分支标签保持短句。"
  ]
}
