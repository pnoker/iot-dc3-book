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
  "id": "fig-2-6",
  "type": "layered",
  "title": "图2-6 智能层在闭环中的推理-规划-执行分工图",
  "purpose": "展示智能层在闭环中承担的三个核心环节及其与平台层的数据/指令交互，并用虚线箭头标注闭环迭代。",
  "audience_takeaway": "读者应理解智能层在闭环中的推理-规划-执行分工图中的主链路、责任边界和工程取舍。",
  "visual_focus": "从执行模块到驱动服务（消息队列），实线箭头的主链路。",
  "layout": "垂直分层布局，自上而下：智能层（内部分为推理、规划、执行三个等宽模块）、平台层（数据中心、管理中心、认证中心）、感知与网络层（驱动服务、现场设备）。",
  "components": [
    {
      "id": "r1",
      "label": "智能层内推理",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "规划→执行→推理构成闭环迭代，箭头…",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "推理模块",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r4",
      "label": "平台层数据中心（拉取位号值），实线…",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "r5",
      "label": "规划模块",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r6",
      "label": "平台层管理中心（查询元数据），实线…",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "r7",
      "label": "执行模块",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r8",
      "label": "平台层数据中心（下发指令），实线箭头",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "r9",
      "label": "平台层数据中心",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "r10",
      "label": "驱动服务（消息队列），实线箭头",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "bus"
    }
  ],
  "connections": [
    {
      "from": "r7",
      "to": "r8",
      "label": "执行模块→平台层数据中心（下发指令…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r9",
      "to": "r10",
      "label": "平台层数据中心→驱动服务（消息队列…",
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
      "id": "data_domain",
      "label": "数据资产域",
      "role": "数据沉淀与治理边界"
    },
    {
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    }
  ],
  "callouts": [
    "智能层内推理→规划→执行→推理构成闭环迭代，箭头带“闭环迭代”标签，使用虚线",
    "推理模块→平台层数据中心（拉取位号值），实线箭头",
    "规划模块→平台层管理中心（查询元数据），实线箭头"
  ],
  "legend": [
    "蓝绿色模块：智能层认知能力",
    "蓝色模块：平台层基础能力或设备接入层",
    "实线箭头：数据或指令流",
    "虚线箭头：闭环迭代"
  ],
  "caption": "图2-6 智能层在闭环中的推理-规划-执行分工图，展示认知环节与平台层基础设施的边界。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
