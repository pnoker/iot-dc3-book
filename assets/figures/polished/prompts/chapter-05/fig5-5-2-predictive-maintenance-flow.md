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
  "id": "fig5-5-2-predictive-maintenance-flow",
  "type": "flowchart",
  "title": "从数据采集到告警触发的预测性维护流程",
  "purpose": "展示预测性维护管道的完整阶段，以及数据流、告警流、模型更新流之间的交互关系",
  "audience_takeaway": "读者应理解从数据采集到告警触发的预测性维护流程中的主链路、责任边界和工程取舍。",
  "visual_focus": "从设备层到决策层：传递评分结果的主链路。",
  "layout": "从左至右水平布局，进程使用圆角矩形，数据存储使用圆柱，判断使用菱形",
  "components": [
    {
      "id": "r1",
      "label": "设备层",
      "type": "edge",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "数据管道：电流数据上传",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "r3",
      "label": "数据管道",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "r4",
      "label": "模型层：历史数据供训练",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "r5",
      "label": "模型层",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r6",
      "label": "评分层：输出预测区间",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r7",
      "label": "评分层",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r8",
      "label": "决策层：传递评分结果",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "decision"
    },
    {
      "id": "r9",
      "label": "决策层",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "decision"
    },
    {
      "id": "r10",
      "label": "反馈回路 → 模型层：确认后执行增…",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "r1",
      "to": "r2",
      "label": "设备层 → 数据管道：电流数据上传",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r3",
      "to": "r4",
      "label": "数据管道 → 模型层：历史数据供训练",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r5",
      "to": "r6",
      "label": "模型层 → 评分层：输出预测区间",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r7",
      "to": "r8",
      "label": "评分层 → 决策层：传递评分结果",
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
    "设备层 → 数据管道：电流数据上传",
    "数据管道 → 模型层：历史数据供训练",
    "模型层 → 评分层：输出预测区间"
  ],
  "legend": [
    "绿色箭头为数据流，红色箭头为告警流，蓝色箭头为模型更新流"
  ],
  "caption": "图5-16 预测性维护管道数据流示意",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "决策节点必须写成可判断的问题或动作，分支标签保持短句。"
  ]
}
