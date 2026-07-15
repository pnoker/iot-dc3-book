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
  "id": "fig-6-1",
  "type": "dataflow",
  "title": "图6-1 物联网REST API端点设计示例（示意）",
  "purpose": "展示物联网后端常见API端点布局，体现读写分离、版本控制、资源型端点设计。",
  "audience_takeaway": "读者应理解物联网REST API端点设计示例（示意）中的主链路、责任边界和工程取舍。",
  "visual_focus": "从device到终点的主链路。",
  "layout": "横向泳道图：左侧外部实体（设备、前端、第三方），中间API端点，右侧内部服务。",
  "components": [
    {
      "id": "r1",
      "label": "device",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "post_data",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "processing",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r4",
      "label": "frontend",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r5",
      "label": "get_devices",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r6",
      "label": "get_history",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r7",
      "label": "thirdparty",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r8",
      "label": "post_rule",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r9",
      "label": "get_alarms",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r10",
      "label": "post_command",
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
      "label": "上报数据",
      "style": "solid",
      "direction": "right"
    },
    {
      "from": "r2",
      "to": "r3",
      "label": "传入",
      "style": "solid",
      "direction": "right"
    },
    {
      "from": "r4",
      "to": "r5",
      "label": "查询",
      "style": "solid",
      "direction": "right"
    },
    {
      "from": "r4",
      "to": "r6",
      "label": "查询",
      "style": "solid",
      "direction": "right"
    },
    {
      "from": "r7",
      "to": "r8",
      "label": "创建规则",
      "style": "solid",
      "direction": "right"
    },
    {
      "from": "r7",
      "to": "r9",
      "label": "查询",
      "style": "solid",
      "direction": "right"
    },
    {
      "from": "r10",
      "to": "command_svc",
      "label": "下发",
      "style": "solid",
      "direction": "right"
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
    "device → post_data（上报数据）",
    "post_data → processing（传入）",
    "frontend → get_devices（查询）"
  ],
  "legend": [
    "外部实体",
    "API端点",
    "内部服务逻辑",
    "请求/数据流方向",
    "对应GET/POST/PUT/DELETE HTTP方法"
  ],
  "caption": "图6-1 物联网REST API端点设计示例（示意）",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
