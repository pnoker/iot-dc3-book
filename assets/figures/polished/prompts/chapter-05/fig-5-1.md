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
  "id": "fig-5-1",
  "type": "layered",
  "title": "图5-1 物联网平台分层架构示意",
  "purpose": "展示从感知层到应用层的标准四层模型，并明确平台层在这一模型中的桥梁位置",
  "audience_takeaway": "读者应理解物联网的四层职责边界，以及数据流和控制流的方向差异。",
  "visual_focus": "数据流的绿色箭头从感知层向上贯穿至应用层，控制流的蓝色箭头反向；平台层内部组件顺序关系用水平箭头表示。",
  "layout": "自下而上四个矩形堆叠，每层宽度一致，颜色不同；平台层内部用四个更小的水平方块表示组件流程。",
  "components": [
    {
      "id": "sensor",
      "label": "感知层",
      "type": "edge",
      "subtitle": "传感器、执行器",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "network",
      "label": "网络层",
      "type": "edge",
      "subtitle": "无线/WAN/有线",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "platform",
      "label": "平台层",
      "type": "platform",
      "subtitle": "设备接入→消息→存储→使能",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "application",
      "label": "应用层",
      "type": "application",
      "subtitle": "大屏/App/AI/系统",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "sensor",
      "to": "network",
      "label": "数据流",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "network",
      "to": "platform",
      "label": "数据",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "platform",
      "to": "application",
      "label": "数据",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "application",
      "to": "platform",
      "label": "控制流",
      "style": "solid",
      "direction": "top-to-bottom"
    },
    {
      "from": "platform",
      "to": "network",
      "label": "控制",
      "style": "solid",
      "direction": "top-to-bottom"
    },
    {
      "from": "network",
      "to": "sensor",
      "label": "控制",
      "style": "solid",
      "direction": "top-to-bottom"
    }
  ],
  "regions": [],
  "callouts": [
    "数据流（绿色实线箭头）: 感知层 → 网络层 → 平台层 → 应用层",
    "控制流（蓝色实线箭头）: 应用层 → 平台层 → 网络层 → 感知层",
    "平台内部流（橙色水平箭头）: 设备接入 → 消息处理 → 存储 → 应用使能"
  ],
  "legend": [
    "绿色箭头: 数据流（上行感知数据）",
    "蓝色箭头: 控制流（下行命令）",
    "橙色水平箭头: 平台层内部处理顺序",
    "背景色：感知层-浅绿，网络层-浅蓝，平台层-浅橙，应用层-浅紫"
  ],
  "caption": "图5-1 物联网平台分层架构示意。感知层采集物理信号并数字化，经网络层传输至平台层；平台层完成协议转换、消息缓冲、规则判断与存储，最后通过API暴露给应用层；应用层提供人机交互与决策支持。",
  "visual_constraints": [
    "节点标签使用短名词，解释性文字放入callouts或正文。",
    "箭头线型统一，不出现多重交叉。",
    "图例置于底部，不遮挡主体。"
  ]
}
