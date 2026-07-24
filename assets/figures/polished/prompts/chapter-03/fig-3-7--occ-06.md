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
  "id": "fig-3-7",
  "type": "layered",
  "title": "图3-7 EPC Gen2标签存储体分层结构",
  "purpose": "展示标签芯片内四个存储区的堆叠关系与各区域典型内容。",
  "audience_takeaway": "读者应理解EPC Gen2标签存储体分层结构中的主链路、责任边界和工程取舍。",
  "visual_focus": "从Reserved到User的主链路。",
  "layout": "垂直堆叠的四层结构，从下往上依次为Reserved、EPC、TID、User。",
  "components": [
    {
      "id": "c1",
      "label": "Reserved",
      "type": "platform",
      "subtitle": "Kill Password（32 bits）+ Acc…",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "c2",
      "label": "EPC",
      "type": "platform",
      "subtitle": "PC bits + EPC序列号（96 bits）+…",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c3",
      "label": "TID",
      "type": "platform",
      "subtitle": "芯片厂商代码 + 型号 + 唯一序列号（64–96 b…",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c4",
      "label": "User",
      "type": "data",
      "subtitle": "用户自定义数据（长度可选）",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "Reserved位于最底层，为其他…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "EPC位于Reserved之上，承…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c3",
      "to": "c4",
      "label": "TID位于EPC之上，存储芯片唯一…",
      "style": "solid",
      "direction": "left-to-right"
    }
  ],
  "regions": [
    {
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    },
    {
      "id": "data_domain",
      "label": "数据资产域",
      "role": "数据沉淀与治理边界"
    }
  ],
  "callouts": [
    "Reserved位于最底层，为其他存储体提供安全基础",
    "EPC位于Reserved之上，承载物品标识",
    "TID位于EPC之上，存储芯片唯一身份"
  ],
  "legend": [
    "Reserved：红色系，表示安全。",
    "EPC：蓝色，表示标识。",
    "TID：绿色，表示身份。",
    "User：灰色，表示扩展。"
  ],
  "caption": "图3-7 EPC Gen2标签存储体分层结构示意",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
