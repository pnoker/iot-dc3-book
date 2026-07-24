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
  "id": "figure-13-4",
  "type": "architecture",
  "title": "数据验证与溯源机制时序图",
  "purpose": "展示数据从传感器产生到链上验证的完整流程，重点突出事件日志的索引作用和验证函数的调用路径。",
  "audience_takeaway": "读者应理解数据验证与溯源机制时序图中的主链路、责任边界和工程取舍。",
  "visual_focus": "从1. 传感器到边缘节点：推送原始数据的主链路。",
  "layout": "纵向时间轴，沿时间顺序从上向下排列各参与方与操作步骤。",
  "components": [
    {
      "id": "r1",
      "label": "1. 传感器",
      "type": "edge",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "边缘节点：推送原始数据",
      "type": "edge",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "database"
    }
  ],
  "connections": [
    {
      "from": "r1",
      "to": "r2",
      "label": "实线箭头，标注“原始数据 JSON…",
      "style": "solid",
      "direction": "request"
    }
  ],
  "regions": [
    {
      "id": "edge_domain",
      "label": "设备与边缘域",
      "role": "现场异构资源边界"
    }
  ],
  "callouts": [
    "1. 传感器 → 边缘节点：推送原始数据（实线箭头，标注“原始数据 JSON”） 2. 边缘节点 → 智能合约：调…"
  ],
  "legend": [
    "实线箭头：交易或直接调用",
    "虚线箭头：事件广播或异步通知",
    "带圆形标记箭头：验证请求与结果",
    "锯齿矩形：区块",
    "圆形图标：参与方"
  ],
  "caption": "数据验证与溯源时序图。数据从传感器经边缘节点上链，合约记录指纹并发出事件；验证者通过对比哈希确认完整性，同时利用事件追溯历史操作。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
