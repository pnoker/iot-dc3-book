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
  "id": "fig-6-5",
  "type": "architecture",
  "title": "图6-5 物联网系统关键决策三元组",
  "purpose": "展示语言、协议、架构三个决策维度在原型阶段与生产阶段的典型差异和迁移路径。",
  "audience_takeaway": "读者应理解物联网系统决策不是孤立选择，而是三个维度互相影响的系统工程。",
  "visual_focus": "从“语言→协议→架构”的递进影响链路，以及每个维度内迁移路径上的关键工程动作。",
  "layout": "三栏并排布局。每栏分上下两个区域：上方“原型阶段”浅蓝底色，下方“生产阶段”深蓝底色；两区域之间用橙色箭头竖直连接，箭头旁标注迁移动作。",
  "components": [
    {
      "id": "c1",
      "label": "语言决策",
      "type": "ai",
      "subtitle": "Python→Java",
      "group": "intelligence_domain",
      "priority": "primary",
      "shape": "decision"
    },
    {
      "id": "c2",
      "label": "协议决策",
      "type": "ai",
      "subtitle": "MQTT+REST→+gRPC",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "decision"
    },
    {
      "id": "c3",
      "label": "架构决策",
      "type": "ai",
      "subtitle": "单体→微服务",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "decision"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "影响协议实现复杂度",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "影响架构边界划分",
      "style": "solid",
      "direction": "left-to-right"
    }
  ],
  "regions": [
    {
      "id": "intelligence_domain",
      "label": "智能决策域",
      "role": "决策三元组的影响域边界"
    }
  ],
  "callouts": [
    "语言选型影响协议实现的复杂度：Python 的 GIL 可能在高并发 gRPC 流场景下成为瓶颈，而 Java 的 Netty 框架更适合实现服务端流。",
    "协议选型直接影响架构边界：不同协议需要不同的接入点，这些接入点必须由 API 网关统一管理。",
    "架构选型决定了各协议层能否独立扩缩容：设备接入层按设备数量水平扩展，数据服务层按消息量扩展。"
  ],
  "legend": [
    "浅蓝底色=原型阶段选项，深蓝底色=生产阶段升级选项。",
    "橙色箭头=迁移路径，标注最短工程动作。",
    "左侧代码文件图标=语言列，中间网络信号图标=协议列，右侧服务器集群图标=架构列。"
  ],
  "caption": "图6-5 从原型到生产的三元决策矩阵。每一列展示了在语言、协议、架构层面，原型阶段和生产阶段分别采用的最佳选项，以及两者之间的最短迁移路径。图中元素来源于本章各节讨论（6.1 语言实践、6.2 协议实践、6.3 架构实践）。",
  "visual_constraints": [
    "最多 9 个主节点（每列 3 个，含阶段和动作）。",
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
