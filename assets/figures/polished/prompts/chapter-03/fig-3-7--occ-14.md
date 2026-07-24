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
  "id": "fig-3-7",
  "type": "architecture",
  "title": "物模型驱动设备互操作的示意图",
  "purpose": "说明物模型作为中间抽象层，如何屏蔽异构设备的协议差异，为上层应用提供统一的数据和服务接口。",
  "audience_takeaway": "读者应理解物模型驱动设备互操作的示意图中的主链路、责任边界和工程取舍。",
  "visual_focus": "从dev-a到app-layer的主链路。",
  "layout": "垂直分层图，从上到下依次为：应用层、物模型层（抽象层）、设备层。",
  "components": [
    {
      "id": "r1",
      "label": "dev-a",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "properties",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "dev-b",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r4",
      "label": "dev-c",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r5",
      "label": "dev-d",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r6",
      "label": "actions",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r7",
      "label": "app-layer",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r8",
      "label": "events",
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
      "label": "映射到‘温度’属性",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r3",
      "to": "r2",
      "label": "映射到‘温度’属性",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r4",
      "to": "r2",
      "label": "映射到‘振动频率’属性",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r5",
      "to": "r6",
      "label": "映射到‘读取标签’服务",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r2",
      "to": "r7",
      "label": "统一输出标准属性",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r6",
      "to": "r7",
      "label": "统一调用标准服务",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r8",
      "to": "r7",
      "label": "统一推送标准事件",
      "style": "dashed",
      "direction": "event"
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
    "dev-a → properties（映射到‘温度’属性）",
    "dev-b → properties（映射到‘温度’属性）",
    "dev-c → properties（映射到‘振动频率’属性）"
  ],
  "legend": [
    "形状=设备层用矩形表示异构设备，物模型层用虚线圆角矩形表示抽象层，应用层用圆形表示应用逻辑。",
    "箭头=从设备到物模型层的箭头表示“能力映射”；从物模型层到应用层的合并箭头表示“统一输出”。",
    "颜色=物模型层元素使用统一色调表示标准化；设备层元素使用不同颜色表示协议差异。"
  ],
  "caption": "图3-7 物模型作为中间抽象层，将异构设备的能力标准化，为上层应用提供统一接口。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
