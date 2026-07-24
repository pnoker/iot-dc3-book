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
  "id": "fig-4-4",
  "type": "layered",
  "title": "图4-4 统一接入层四层架构",
  "purpose": "展示统一接入层内部的四个功能层以及各层间的接口与数据流向。",
  "audience_takeaway": "读者应理解统一接入层四层架构中的主链路、责任边界和工程取舍。",
  "visual_focus": "从设备抽象层向下到协议泛化层的 read/write的主链路。",
  "layout": "自上而下竖向堆叠，层间用实线分隔并标注接口箭头。",
  "components": [
    {
      "id": "r1",
      "label": "设备抽象层向下",
      "type": "edge",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "数据解析层的 toStandard…",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "r3",
      "label": "数据解析层向下",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "r4",
      "label": "连接管理层的 connect/ke…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r5",
      "label": "连接管理层向下",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r6",
      "label": "协议泛化层的 read/write",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r7",
      "label": "左侧标注'",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r8",
      "label": "方向向下'，右侧标注'数据上报方向…",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    }
  ],
  "connections": [
    {
      "from": "r1",
      "to": "tostandardpayl",
      "label": "设备抽象层向下调用数据解析层的 t…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r3",
      "to": "connect_keepal",
      "label": "数据解析层向下调用连接管理层的 c…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r5",
      "to": "r6",
      "label": "连接管理层向下调用协议泛化层的 r…",
      "style": "solid",
      "direction": "request"
    }
  ],
  "regions": [
    {
      "id": "edge_domain",
      "label": "设备与边缘域",
      "role": "现场异构资源边界"
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
    "设备抽象层向下调用数据解析层的 toStandardPayload/fromStandardPayload",
    "数据解析层向下调用连接管理层的 connect/keepAlive",
    "连接管理层向下调用协议泛化层的 read/write"
  ],
  "legend": [
    "浅绿：设备抽象层；浅蓝：数据解析层；浅黄：连接管理层；浅橙：协议泛化层",
    "实线箭头：同步调用依赖；虚线箭头：异步数据回调",
    "最上层和最下层分别加指向外的宽箭头表示上下衔接"
  ],
  "caption": "图4-4 统一接入层通过四层解耦将协议差异逐层收口，上层对下层是调用依赖，下层对上层通过回调上送数据。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
