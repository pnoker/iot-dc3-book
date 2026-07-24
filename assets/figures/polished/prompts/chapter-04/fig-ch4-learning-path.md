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
  "id": "fig-ch4-learning-path",
  "type": "layered",
  "title": "图4-5 延伸阅读三圈学习路径",
  "purpose": "将推荐资源按学习阶段分层，展示从权威认知到动手实践再到行业视野的进阶路线，帮助读者定位当前学习阶段。",
  "audience_takeaway": "读者应理解延伸阅读三圈学习路径中的主链路、责任边界和工程取舍。",
  "visual_focus": "从将推荐资源按学习阶段分层，展示从权…到动手实践再到行业视野的进阶路线，帮…的主链路。",
  "layout": "vertical stacked",
  "components": [
    {
      "id": "r1",
      "label": "将推荐资源按学习阶段分层，展示从权…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "动手实践再到行业视野的进阶路线，帮…",
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
      "label": "将推荐资源按学习阶段分层，展示从权…",
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
    "将推荐资源按学习阶段分层，展示从权威认知到动手实践再到行业视野的进阶路线，帮助读者定位当前学习阶段"
  ],
  "legend": [
    "蓝色=核心能力；橙色=智能/风险路径。"
  ],
  "caption": "图4-5 延伸阅读三圈学习路径。从第一圈蓝底（官方标准）开始，反复验证后进入第二圈绿底（动手实践），最后拓展到第三圈橙底（行业视野）。每圈内的条目旁标注了与本章的对应关系。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
