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
  "id": "fig-11-5",
  "type": "sequence",
  "title": "图11-5 火灾应急响应事件流转时序（假设场景）",
  "purpose": "说明火灾事件从传感器报警到跨部门调度的消息传递顺序，突出边缘计算和自动路由对响应时间的压缩作用。",
  "audience_takeaway": "读者应理解自动化链路如何规避人工转接带来的延迟，以及边缘节点在压减感知到响应时间中的位置。",
  "visual_focus": "从传感器报警到边缘判定再到自动路由的路径。",
  "layout": "参与者横向排列，时间轴从上到下。主参与者在顶部，生命线向下延伸。",
  "components": [
    {
      "id": "sensor",
      "label": "烟雾传感器",
      "type": "edge",
      "group": "seq_edge",
      "priority": "primary",
      "shape": "actor"
    },
    {
      "id": "edge_node",
      "label": "边缘计算节点",
      "type": "edge",
      "subtitle": "本地规则引擎",
      "group": "seq_edge",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "cloud_coord",
      "label": "云端协同层",
      "type": "platform",
      "subtitle": "事件路由",
      "group": "seq_cloud",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "fire_sys",
      "label": "消防系统",
      "type": "application",
      "group": "seq_cloud",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "traffic_sys",
      "label": "交通系统",
      "type": "application",
      "group": "seq_cloud",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "sensor",
      "to": "edge_node",
      "label": "上报警值",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "edge_node",
      "to": "cloud_coord",
      "label": "推送事件摘要",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "cloud_coord",
      "to": "fire_sys",
      "label": "派单指令",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "cloud_coord",
      "to": "traffic_sys",
      "label": "信号控制指令",
      "style": "solid",
      "direction": "request"
    }
  ],
  "regions": [
    {
      "id": "seq_edge",
      "label": "设备与边缘域",
      "role": "现场探测与判断边界"
    },
    {
      "id": "seq_cloud",
      "label": "云端协同域",
      "role": "跨部门路由边界"
    }
  ],
  "callouts": [
    "烟雾传感器向边缘节点上报数据（温度、浓度）。",
    "边缘节点运行规则引擎判定事件类型。",
    "边缘节点向云端协同层推送事件摘要。"
  ],
  "legend": [
    "矩形=参与者；实线箭头=同步消息"
  ],
  "caption": "图11-5 自动化链路的关键在于边缘节点完成本地判定（第2步），云端协同层完成自动事件路由（第4步），两地均无人工转接环节。",
  "visual_constraints": [
    "最多6个参与者，标签简短。",
    "图例放在底部。"
  ]
}
