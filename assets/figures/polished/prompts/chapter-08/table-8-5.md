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
  "id": "table-8-5",
  "type": "matrix",
  "title": "多租户隔离强度对比",
  "purpose": "对比三种主要隔离维度在不同隔离强度（低/中/高）下的实现方式、跨租户风险、资源效率和运维复杂度",
  "audience_takeaway": "读者应理解多租户隔离强度对比中的主链路、责任边界和工程取舍。",
  "visual_focus": "从进入下一判断到进入下一判断的主链路。",
  "layout": "表格，行为三种维度（数据隔离、计算资源隔离、网络隔离），每行三个强度等级（低/中/高），列包含典型实现方式、跨租户风险、资源效率高低、运维复杂度高低四项指标",
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
    },
    {
      "id": "c3",
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
      "label": "同一行内从左到右隔离强度递增，跨租…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "资源效率单向递减，运维复杂度单向递增",
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
    "同一行内从左到右隔离强度递增，跨租户风险递减",
    "资源效率单向递减，运维复杂度单向递增"
  ],
  "legend": [
    "低强度使用灰色背景，中强度使用浅蓝色，高强度使用深蓝色；行名加粗并加底色以区分维度"
  ],
  "caption": "表8-5 多租户隔离强度对比（假设场景：智能家居平台“智家云”）",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
