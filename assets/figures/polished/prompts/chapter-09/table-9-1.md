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
  "id": "table-9-1",
  "type": "matrix",
  "title": "协议选择对比表",
  "purpose": "从传输层、QoS能力、延时特征、功耗水平、典型场景五个维度快速对比主流物联网应用层协议，辅助选型决策。",
  "audience_takeaway": "读者应理解协议选择对比表中的主链路、责任边界和工程取舍。",
  "visual_focus": "从传输层、QoS能力、延时特征、功耗水平、典型场景五个维度快速对比主流物联网应用层协议，辅助选…",
  "layout": "两栏布局，左列为维度标签，右列每个协议构成一个着色列（共5列），顶部固定表头行。",
  "components": [
    {
      "id": "c1",
      "label": "行",
      "type": "edge",
      "subtitle": "QoS 0/1/2；延时中等；功耗中等；智能家居、车联…",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "bus"
    }
  ],
  "connections": [],
  "regions": [
    {
      "id": "edge_domain",
      "label": "设备与边缘域",
      "role": "现场异构资源边界"
    }
  ],
  "callouts": [
    "每列体现协议在五个维度上的相对表现，行内横向比较各协议的差异"
  ],
  "legend": [
    "每列的功耗栏用1-3格电池图标示意相对等级（1格=极低，3格=高）。"
  ],
  "caption": "表9-1 主流物联网应用层协议多维对比",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
