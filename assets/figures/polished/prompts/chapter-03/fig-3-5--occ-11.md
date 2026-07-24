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
  "id": "fig-3-5",
  "type": "flowchart",
  "title": "图3-5 边缘节点数据预处理与过滤流程",
  "purpose": "展示从原始传感器输入到最终输出分支的完整数据管道，帮助读者理解滤波、聚合、异常判定三个环节如何串联并产生不同分支。",
  "audience_takeaway": "读者应理解边缘节点数据预处理与过滤流程中的主链路、责任边界和工程取舍。",
  "visual_focus": "从raw到cloud的主链路。",
  "layout": "从上至下，数据流方向用箭头连接各处理节点",
  "components": [
    {
      "id": "r1",
      "label": "raw",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "filter",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "filtered",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r4",
      "label": "aggregate",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r5",
      "label": "aggregated",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r6",
      "label": "anomaly",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r7",
      "label": "normal_path",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r8",
      "label": "alert_path",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r9",
      "label": "cloud",
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
      "label": "主链路",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r2",
      "to": "r3",
      "label": "主链路",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r3",
      "to": "r4",
      "label": "主链路",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r4",
      "to": "r5",
      "label": "主链路",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r5",
      "to": "r6",
      "label": "主链路",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r6",
      "to": "r7",
      "label": "否（正常）",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r6",
      "to": "r8",
      "label": "是（异常）",
      "style": "risk",
      "direction": "request"
    },
    {
      "from": "r7",
      "to": "r9",
      "label": "主链路",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r8",
      "to": "r9",
      "label": "带事件编号",
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
    "raw → filter",
    "filter → filtered",
    "filtered → aggregate"
  ],
  "legend": [
    "蓝色=核心平台/主链路；青绿色=设备与边缘；橙色=AI/风险/关键决策。"
  ],
  "caption": "图3-5 边缘节点数据预处理与过滤流程。原始数据先经过滑动平均滤波去除噪声，再聚合为特征值，最后进行异常判定。正常数据按固定周期推送云平台；异常数据触发本地动作并打标上传。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "决策节点必须写成可判断的问题或动作，分支标签保持短句。"
  ]
}
