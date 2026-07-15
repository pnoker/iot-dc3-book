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
  "id": "fig-9-3",
  "type": "sequence",
  "title": "图9-3 MQTT会话连接与心跳交互示意",
  "purpose": "展示客户端与Broker之间会话建立、心跳保活、断线检测、遗嘱执行、重连与会话恢复的完整流程。",
  "audience_takeaway": "理解会话持久化、心跳超时判定以及重连策略如何配合恢复会话。",
  "visual_focus": "从Client重连到Broker推送离线缓存消息的主链路。",
  "layout": "自上而下时间轴，左侧Client生命线，右侧Broker生命线，右侧偏下灰色Subscriber。",
  "components": [
    {
      "id": "client",
      "label": "Client (sensor01)",
      "type": "edge",
      "subtitle": "MQTT客户端设备",
      "group": "client_domain",
      "priority": "primary",
      "shape": "actor"
    },
    {
      "id": "broker",
      "label": "Broker",
      "type": "platform",
      "subtitle": "MQTT代理服务器",
      "group": "broker_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "subscriber",
      "label": "Subscriber",
      "type": "external",
      "subtitle": "遗嘱消息订阅者",
      "priority": "normal",
      "shape": "actor"
    }
  ],
  "connections": [
    {
      "from": "client",
      "to": "broker",
      "label": "CONNECT (CleanSession=false, KA=60s)",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "broker",
      "to": "client",
      "label": "CONNACK (SessionPresent=false)",
      "style": "solid",
      "direction": "response"
    },
    {
      "from": "broker",
      "to": "subscriber",
      "label": "PUBLISH (Will Message)",
      "style": "dashed",
      "direction": "event"
    },
    {
      "from": "client",
      "to": "client",
      "label": "重连策略 (1s,2s,4s...)",
      "style": "dashed",
      "direction": "event"
    },
    {
      "from": "client",
      "to": "broker",
      "label": "CONNECT (Reconnect)",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "broker",
      "to": "client",
      "label": "CONNACK (SessionPresent=true)",
      "style": "solid",
      "direction": "response"
    },
    {
      "from": "broker",
      "to": "client",
      "label": "离线缓存消息",
      "style": "solid",
      "direction": "request"
    }
  ],
  "regions": [
    {
      "id": "client_domain",
      "label": "客户端域",
      "role": "发起连接与消息"
    },
    {
      "id": "broker_domain",
      "label": "Broker域",
      "role": "消息路由与状态管理"
    }
  ],
  "callouts": [
    "CONNECT/CONNACK：同步请求-确认",
    "Broker心跳超时：1.5倍KA（示例值90s）",
    "遗嘱消息广播给所有订阅者"
  ],
  "legend": [
    "青绿色：客户端；蓝色：Broker；灰色：第三方订阅者",
    "实线箭头：同步请求/响应；虚线箭头：异步广播或内部自消息"
  ],
  "caption": "图9-3 MQTT会话连接与心跳交互示意。展示Client（sensor01）与Broker之间从连接建立、心跳维持、网络断线、遗嘱执行到指数退避重连并恢复会话的完整过程。Keep Alive设为60秒，Broker以1.5倍超时判定离线（约90秒）。重连后Broker推送断线期间缓存的QoS 1/2消息。",
  "visual_constraints": [
    "节点标签用短英文，解释性文字放入正文及callouts",
    "图例放在底部，不遮挡主体"
  ]
}
