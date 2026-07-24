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
  "id": "fig-11-2-rsu-obu-sequence",
  "type": "sequence",
  "title": "图11-2 RSU与OBU通信流程",
  "purpose": "展示信号机、RSU、雷达、OBU、车载HMI以及ADAS域控制器之间的消息交互顺序和时序关系",
  "audience_takeaway": "读者应理解RSU与OBU通信流程中的主链路、责任边界和工程取舍。",
  "visual_focus": "从信号机到终点的主链路。",
  "layout": "垂直方向，六条生命线，自左向右排列",
  "components": [
    {
      "id": "signal_controller",
      "label": "信号机",
      "type": "edge",
      "subtitle": "灯色输出",
      "group": "roadside_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "rsu",
      "label": "RSU",
      "type": "platform",
      "subtitle": "协议转换与广播",
      "group": "roadside_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "radar",
      "label": "雷达",
      "type": "edge",
      "subtitle": "目标检测",
      "group": "roadside_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "obu",
      "label": "OBU",
      "type": "platform",
      "subtitle": "消息接收与融合",
      "group": "vehicle_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "hmi",
      "label": "HMI",
      "type": "application",
      "subtitle": "驾驶员提示",
      "group": "vehicle_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "adas",
      "label": "ADAS",
      "type": "ai",
      "subtitle": "路径决策",
      "group": "vehicle_domain",
      "priority": "normal",
      "shape": "decision"
    }
  ],
  "connections": [
    {
      "from": "signal_controller",
      "to": "rsu",
      "label": "灯色数据",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "radar",
      "to": "rsu",
      "label": "目标列表",
      "style": "dashed",
      "direction": "request"
    },
    {
      "from": "rsu",
      "to": "obu",
      "label": "SPAT/RSI广播",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "obu",
      "to": "hmi",
      "label": "显示提示",
      "style": "solid",
      "direction": "response"
    },
    {
      "from": "obu",
      "to": "adas",
      "label": "决策输入",
      "style": "solid",
      "direction": "response"
    }
  ],
  "regions": [
    {
      "id": "roadside_domain",
      "label": "路侧域",
      "role": "路侧设备与信号机控制边界"
    },
    {
      "id": "vehicle_domain",
      "label": "车载域",
      "role": "车载通信与决策边界"
    }
  ],
  "callouts": [
    "信号机的灯色数据通过串口输出，RSU轮询读取。",
    "SPAT和RSI消息通过PC5广播，不确认接收。",
    "ADAS域控制器直接利用SPAT相位信息进行绿波或停车决策。"
  ],
  "legend": [
    "实线箭头: 确认的消息流或数据流",
    "虚线箭头: 非周期广播或可选链路",
    "双竖线: 表示PC5广播通道"
  ],
  "caption": "图11-2 RSU与OBU通信流程图。展示了信号机、路侧雷达、RSU、OBU、车载HMI和ADAS域控制器之间的消息流向和时序。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
