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
  "id": "figure-8-7",
  "type": "architecture",
  "title": "物联网微隔离架构示意图",
  "purpose": "展示从设备层到策略编排层的四层分层模型，说明微分段如何通过SDN控制器实现逐设备级别的隔离规则，防止横向移动。",
  "audience_takeaway": "读者应理解物联网微隔离架构示意图中的主链路、责任边界和工程取舍。",
  "visual_focus": "从layer1到layer1的主链路。",
  "layout": "四层堆叠分层，自底向上依次为物理设备层、接入网关层、微分段控制层、全局策略编排层，层间用带箭头的实线或虚线连接。",
  "components": [
    {
      "id": "r1",
      "label": "layer1",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "layer2",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "layer3",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r4",
      "label": "layer4",
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
      "label": "主链路",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r2",
      "to": "r3",
      "label": "主链路",
      "style": "dashed",
      "direction": "request"
    },
    {
      "from": "r3",
      "to": "r2",
      "label": "主链路",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r4",
      "to": "r3",
      "label": "主链路",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r4",
      "to": "r1",
      "label": "主链路",
      "style": "dashed",
      "direction": "request"
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
    "layer1 → layer2",
    "layer2 → layer3",
    "layer3 → layer2"
  ],
  "legend": [
    "分层组件，每个层包含多个功能实体",
    "策略或配置数据的流向",
    "控制咨询或动态调整的流向"
  ],
  "caption": "图8-7 物联网微隔离架构示意图。四层模型从设备到策略编排依次递进，微分段控制层是核心决策点。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
