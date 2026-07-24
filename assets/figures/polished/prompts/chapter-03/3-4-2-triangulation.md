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
  "id": "3-4-2-triangulation",
  "type": "architecture",
  "title": "三角测量定位原理示意",
  "purpose": "说明三点定位的几何原理以及实际测量噪声导致的交叠区域，引出最小二乘修正的必要性。",
  "audience_takeaway": "读者应理解三角测量定位原理示意中的主链路、责任边界和工程取舍。",
  "visual_focus": "说明三点定位的几何原理以及实际测量噪声导致的交叠区域，引出最小二乘修正的必要性",
  "layout": "architecture",
  "components": [
    {
      "id": "c1",
      "label": "三角测量定位原理示意",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    }
  ],
  "connections": [],
  "regions": [
    {
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    }
  ],
  "callouts": [
    "说明三点定位的几何原理以及实际测量噪声导致的交叠区域，引出最小二乘修正的必要性"
  ],
  "legend": [
    "蓝色=核心能力；橙色=智能/风险路径。"
  ],
  "caption": "图3-9 三角测量定位原理示意图。三圆在理想条件下应精确交于一点，但实际测量存在RSSI波动或ToA时钟误差，导致交叠区域出现，可借助最小二乘法计算误差平方和最小的点作为最终坐标。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
