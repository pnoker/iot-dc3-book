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
  "id": "fig1-6",
  "type": "architecture",
  "title": "传统物联网端-云架构与AIoT边-端-云协同架构对比",
  "purpose": "直观对比大模型介入前后物联网拓扑结构的演变，突出边缘层作为推理枢纽的角色，以及数据流和信息流方向的变化。",
  "audience_takeaway": "读者应理解传统物联网端-云架构与AIoT边-端-云协同架构对比中的主链路、责任边界和工程取舍。",
  "visual_focus": "从传统架构=name=感知层到AIoT新架构=name=端侧的主链路。",
  "layout": "架构布局，强调边界、组件职责和主链路。",
  "components": [
    {
      "id": "c1",
      "label": "传统架构=name=感知层",
      "type": "edge",
      "subtitle": "shape=box；color=#E3F2FD；lab…",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "database"
    },
    {
      "id": "c2",
      "label": "AIoT新架构=name=端侧",
      "type": "edge",
      "subtitle": "shape=box；color=#E3F2FD；lab…",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "decision"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "传统架构=from=感知层",
      "style": "solid",
      "direction": "left-to-right"
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
    "传统架构=from=感知层",
    "to=云平台层",
    "color=#90CAF9"
  ],
  "legend": [
    "端侧设备: 感知、执行、状态上报",
    "边缘侧节点: 实时推理、本地决策、控制闭环",
    "云端服务: 大模型、知识库、管理和训练",
    "数据上传或事件上报",
    "实时控制或指令下发",
    "模型或知识更新"
  ],
  "caption": "图1-6 传统物联网端-云架构与AIoT边-端-云协同架构对比。左侧传统架构为两层，数据流和控制流直接往返于端云之间。右侧AIoT新架构引入边缘侧作为实时推理和决策枢纽，端侧与云侧通过边缘侧间接交互，云侧主要负责模型训练与知识更新，并定期将更新下推至边缘侧。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
