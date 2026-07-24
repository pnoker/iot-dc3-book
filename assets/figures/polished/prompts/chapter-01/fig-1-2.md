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
  "id": "fig-1-2",
  "type": "topology",
  "title": "移动互联网应用生态示意",
  "purpose": "展示移动互联网时代以用户为中心的星形应用生态，突出“人-应用-服务”的连接闭环。",
  "audience_takeaway": "读者应理解移动互联网应用生态示意中的主链路、责任边界和工程取舍。",
  "visual_focus": "从用户到移动支付的主链路。",
  "layout": "星形拓扑布局。中心节点为用户，五个外围节点分别为即时通信、社交媒体、移动支付、地图/出行和短视频应用模块。各外围模块之间存在虚线连接（如社交平台内嵌支付功能）。",
  "components": [
    {
      "id": "r1",
      "label": "用户",
      "type": "application",
      "group": "application_domain",
      "priority": "primary",
      "shape": "actor"
    },
    {
      "id": "r2",
      "label": "即时通信",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "社交媒体",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r4",
      "label": "移动支付",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r5",
      "label": "地图/出行",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r6",
      "label": "短视频",
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
      "label": "聊天/红包",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r1",
      "to": "r3",
      "label": "分享/点赞",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r1",
      "to": "r4",
      "label": "扫码支付/转账",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r1",
      "to": "r5",
      "label": "导航/约车",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r1",
      "to": "r6",
      "label": "拍摄/发布",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r3",
      "to": "r4",
      "label": "内嵌支付",
      "style": "solid",
      "direction": "request"
    }
  ],
  "regions": [
    {
      "id": "application_domain",
      "label": "业务应用域",
      "role": "业务价值交付边界"
    },
    {
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    }
  ],
  "callouts": [
    "用户 → 即时通信（聊天/红包）",
    "用户 → 社交媒体（分享/点赞）",
    "用户 → 移动支付（扫码支付/转账）"
  ],
  "legend": [
    "中心节点：用户（圆形，黄色）；外围节点：应用模块（矩形，蓝绿色调）；实线箭头从用户指向各应用模块；虚线表示模块间的交叉连接。"
  ],
  "caption": "该图展示移动互联网时代以用户为中心的应用生态。即时通信维系熟人关系，社交媒体扩大社交半径，移动支付将社交关系延伸至交易，地图/出行解决物理移动需求，短视频成为新的内容消费和社交入口。模块间交叉连接的含义是：一个应用内往往集成多种功能（例如社交媒体可以内嵌支付入口）。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
