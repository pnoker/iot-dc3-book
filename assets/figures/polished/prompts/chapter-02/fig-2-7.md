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
  "id": "fig-2-7",
  "type": "sequence",
  "title": "五大中心协同流程时序图（智能灌溉场景）",
  "purpose": "展示从设备注册、元数据配置、数据上报、规则触发、AI推理到指令下发的完整时序，涵盖Gateway、Auth、Manager、Data、Agentic、驱动和现场设备七个参与者。图中每步交互都用编号标注，便于文字对照。重点突出闭环中位号值（PointValue）的传递路径。",
  "audience_takeaway": "读者应理解五大中心协同流程时序图（智能灌溉场景）中的主链路、责任边界和工程取舍。",
  "visual_focus": "从现场设备到Agentic的主链路。",
  "layout": "horizontal",
  "components": [
    {
      "id": "r1",
      "label": "现场设备",
      "type": "edge",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "Gateway",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "Auth",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r4",
      "label": "运维人员",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r5",
      "label": "Manager",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r6",
      "label": "Data",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r7",
      "label": "Agentic",
      "type": "ai",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r8",
      "label": "驱动",
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
      "label": "① 注册请求（设备ID/初始令牌）",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r2",
      "to": "r3",
      "label": "② 验证设备身份",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r3",
      "to": "r2",
      "label": "③ 返回JWT凭证",
      "style": "dashed",
      "direction": "response"
    },
    {
      "from": "r2",
      "to": "r1",
      "label": "④ 认证成功允许接入",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r4",
      "to": "r5",
      "label": "⑤ 创建设备元数据/位号/规则",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r5",
      "to": "r6",
      "label": "⑥ 同步规则配置",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r1",
      "to": "r2",
      "label": "⑦ 上报传感器数据（原始值）",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r2",
      "to": "r6",
      "label": "⑧ 转发归一化数据（PointVa…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r6",
      "to": "r6",
      "label": "⑨ 写入时序库并触发规则检查",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r6",
      "to": "r7",
      "label": "⑩ 推送推理由中心介入",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r7",
      "to": "r6",
      "label": "⑪ 查询历史湿度（Tool-Cal…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r6",
      "to": "r7",
      "label": "⑫ 返回时序数据",
      "style": "dashed",
      "direction": "response"
    }
  ],
  "regions": [
    {
      "id": "edge_domain",
      "label": "设备与边缘域",
      "role": "现场异构资源边界"
    },
    {
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    },
    {
      "id": "data_domain",
      "label": "数据资产域",
      "role": "数据沉淀与治理边界"
    },
    {
      "id": "intelligence_domain",
      "label": "智能决策域",
      "role": "模型、规则与 Agent 边界"
    }
  ],
  "callouts": [
    "现场设备 → Gateway（① 注册请求（设备ID/初始令牌））",
    "Gateway → Auth（② 验证设备身份）",
    "Auth → Gateway（③ 返回JWT凭证）"
  ],
  "legend": [
    "description=箭头线型说明：实线 `->` 表示同步调用，虚线 `-->` 表示异步返回，点线 `..` 表示内部处理。颜色与actor对应：Gateway（暖橙）、Auth（紫色）、Manager（绿色）、Data（蓝色）、Agentic（红色）、驱动/设备（青色）。右侧额外标注：所有异步返回均携带最终结果或错误码。"
  ],
  "caption": "图2-7 五大中心协同流程时序图（智能灌溉场景）",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
