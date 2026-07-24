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
  "id": "fig-key-lifecycle",
  "type": "flowchart",
  "title": "图8-5 密钥生命周期管理与云边协同流程",
  "purpose": "展示物联网平台中密钥从生成到销毁的完整生命周期，强调云端和边缘的协同密钥管理流程，帮助读者理解不同角色的职责和密钥状态转换。",
  "audience_takeaway": "读者应理解密钥生命周期管理与云边协同流程中的主链路、责任边界和工程取舍。",
  "visual_focus": "从进入下一判断到进入下一判断的主链路。",
  "layout": "从上到下的泳道流程图",
  "components": [
    {
      "id": "c1",
      "label": "进入下一判断",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "c2",
      "label": "进入下一判断",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c3",
      "label": "进入下一判断",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c4",
      "label": "进入下一判断",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "主链路",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "主链路",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c3",
      "to": "c4",
      "label": "主链路",
      "style": "solid",
      "direction": "left-to-right"
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
    "展示物联网平台中密钥从生成到销毁的完整生命周期，强调云端和边缘的协同密钥管理流程，帮助读者理解不同角色的职责和密钥…"
  ],
  "legend": [
    "颜色=使用中（绿色）、轮换中（黄色）、已撤销/停用（红色）、待销毁（灰色）",
    "箭头=实线箭头表示直接操作，虚线箭头表示通过TLS加密通道传输"
  ],
  "caption": "图8-5 密钥生命周期管理与云边协同流程",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "决策节点必须写成可判断的问题或动作，分支标签保持短句。"
  ]
}
