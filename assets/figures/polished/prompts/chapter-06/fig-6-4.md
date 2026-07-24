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
  "id": "fig-6-4",
  "type": "layered",
  "title": "微服务可观测性分层架构",
  "purpose": "展示从代码规范到告警通知的完整监控链路，说明各层组件及数据流",
  "audience_takeaway": "读者应理解微服务可观测性分层架构中的主链路、责任边界和工程取舍。",
  "visual_focus": "从进入下一判断到进入下一判断的主链路。",
  "layout": "三层从左到右堆叠，每层包含对应组件框",
  "components": [
    {
      "id": "c1",
      "label": "进入下一判断",
      "type": "security",
      "subtitle": "可视化指标面板与告警通知，支持钉钉/邮件/Pa…",
      "group": "governance_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "c2",
      "label": "进入下一判断",
      "type": "data",
      "subtitle": "Prometheus pull 模式拉取 me…",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "c3",
      "label": "进入下一判断",
      "type": "platform",
      "subtitle": "每个微服务暴露 Prometheus 端点和自…",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "Service A 和 Servi…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "Prometheus 将聚合后的数…",
      "style": "solid",
      "direction": "left-to-right"
    }
  ],
  "regions": [
    {
      "id": "governance_domain",
      "label": "治理与安全域",
      "role": "风险控制与责任边界"
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
    "Service A 和 Service B 的 metrics 被 Prometheus 定期拉取",
    "Prometheus 将聚合后的数据供给 Grafana 展示",
    "Alertmanager 根据 Prometheus 告警规则发送通知到外部通道"
  ],
  "legend": [
    "红色下层：微服务组件（指标提供方）",
    "绿色中间层：基础设施（采集与存储）",
    "灰色上层：终端展示（仪表盘与告警）"
  ],
  "caption": "从代码规范到告警通知的完整监控链路",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
