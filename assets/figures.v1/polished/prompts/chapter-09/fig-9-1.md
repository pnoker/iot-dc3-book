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
  "id": "fig-9-1",
  "type": "layered",
  "title": "物联网协议栈与分类图",
  "purpose": "展示物联网四层参考架构与应用层协议在其中的位置，以及应用层协议按通信模型的分类",
  "audience_takeaway": "读者应理解物联网协议栈与分类图中的主链路、责任边界和工程取舍。",
  "visual_focus": "从起点到终点的主链路。",
  "layout": "从上到下五层，每层以水平色块表示，层间用箭头连接，方向从下到上表示数据流向",
  "components": [
    {
      "id": "c1",
      "label": "感知层",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "c2",
      "label": "无线接入",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c3",
      "label": "网络层",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c4",
      "label": "传输层",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c5",
      "label": "应用层协议 (通信模型分类)",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "layer_1",
      "to": "layer_2",
      "label": "Layer 1 (感知层) → L…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "layer_2",
      "to": "layer_3",
      "label": "Layer 2 (无线接入) →…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "layer_3",
      "to": "layer_4_ip",
      "label": "Layer 3 (网络层) → L…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "layer_4",
      "to": "layer_5",
      "label": "Layer 4 (传输层) → L…",
      "style": "solid",
      "direction": "request"
    }
  ],
  "regions": [
    {
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    },
    {
      "id": "intelligence_domain",
      "label": "智能决策域",
      "role": "模型、规则与 Agent 边界"
    }
  ],
  "callouts": [
    "Layer 1 (感知层) → Layer 2 (无线接入): 传感器数据通过无线网络上传",
    "Layer 2 (无线接入) → Layer 3 (网络层): 无线帧封装为 IP 分组",
    "Layer 3 (网络层) → Layer 4 (传输层): IP 分组经 TCP/UDP 封装"
  ],
  "legend": [
    "颜色区分通信模型: 左侧蓝色系 (发布/订阅) / 右侧橙色系 (请求/响应); 传输层灰色表示 TCP 与 UDP 两种选项"
  ],
  "caption": "图9-1 物联网协议栈与分类图。应用层协议定义消息格式与交互模式，运行在 TCP/UDP 之上，与底层无线技术无关。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
