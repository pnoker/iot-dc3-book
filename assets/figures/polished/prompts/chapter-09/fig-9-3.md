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
  "id": "fig-9-3",
  "type": "architecture",
  "title": "图9-3 CoAP消息格式与选项示意",
  "purpose": "展示CoAP消息的紧凑二进制格式，与HTTP的冗长文本头部形成对比，直观解释CoAP如何实现轻量级传输。",
  "audience_takeaway": "读者应理解CoAP消息格式与选项示意中的主链路、责任边界和工程取舍。",
  "visual_focus": "从HTTP部分到CoAP部分的主链路。",
  "layout": "分层条块布局。上半部分展示一条等价的HTTP GET请求文本头部，下半部分展示一条CoAP CON GET消息的二进制布局。",
  "components": [
    {
      "id": "c1",
      "label": "HTTP部分",
      "type": "ai",
      "subtitle": "显示一条简化的HTTP GET请求头部文本，约…",
      "group": "intelligence_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "c2",
      "label": "CoAP部分",
      "type": "platform",
      "subtitle": "显示一条等价的CoAP CON GET请求的二…",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "bus"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "两条消息完成相同的“查询温度资源”…",
      "style": "solid",
      "direction": "left-to-right"
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
    "两条消息完成相同的“查询温度资源”功能，但CoAP的载荷体积不足HTTP的十分之一"
  ],
  "legend": [
    "CoAP头部各字段用不同颜色区分：固定头部（蓝色）、Token（绿色）、Options（橙色）、Payload（浅灰）。HTTP头部用单色示意。"
  ],
  "caption": "CoAP固定头最小4字节，典型请求头在10–20字节之间（资料：[S1]）；HTTP即使最简请求也超过100字节。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
