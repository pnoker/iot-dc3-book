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
  "id": "fig-8-7",
  "type": "architecture",
  "title": "本章参考资料分类导图",
  "purpose": "帮助读者快速定位本书研究资料包中 12 条参考资料对应的安全主题域，理解各参考资料的主要覆盖范围。",
  "audience_takeaway": "读者应理解本章参考资料分类导图中的主链路、责任边界和工程取舍。",
  "visual_focus": "从[S9]到终点的主链路。",
  "layout": "two_column_vertical",
  "components": [
    {
      "id": "r1",
      "label": "[S9]",
      "type": "platform",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "设备安全与认证",
      "type": "edge",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r3",
      "label": "[S12]",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r4",
      "label": "[S1]",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r5",
      "label": "通信加密与认证",
      "type": "security",
      "group": "governance_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r6",
      "label": "[S10]",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r7",
      "label": "[S11]",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r8",
      "label": "[S5]",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r9",
      "label": "协议安全问题",
      "type": "security",
      "group": "governance_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r10",
      "label": "[S6]",
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
      "label": "核心支撑",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r3",
      "to": "r2",
      "label": "扩展实践",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r4",
      "to": "r5",
      "label": "核心定义",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r6",
      "to": "r5",
      "label": "实践要点",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r7",
      "to": "r5",
      "label": "协议细节",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r8",
      "to": "r9",
      "label": "原理剖析",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r10",
      "to": "r9",
      "label": "工程取舍",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "s2",
      "to": "rbac",
      "label": "核心方案",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "s3",
      "to": "rbac",
      "label": "深度链接",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "s4",
      "to": "ai",
      "label": "接口规范",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "s8",
      "to": "ai",
      "label": "硬约束",
      "style": "solid",
      "direction": "request"
    }
  ],
  "regions": [
    {
      "id": "platform_domain",
      "label": "平台服务域",
      "role": "核心服务能力边界"
    },
    {
      "id": "edge_domain",
      "label": "设备与边缘域",
      "role": "现场异构资源边界"
    },
    {
      "id": "governance_domain",
      "label": "治理与安全域",
      "role": "风险控制与责任边界"
    }
  ],
  "callouts": [
    "[S9] → 设备安全与认证（核心支撑）",
    "[S12] → 设备安全与认证（扩展实践）",
    "[S1] → 通信加密与认证（核心定义）"
  ],
  "legend": [
    "圆角矩形：安全主题领域（共 6 个）",
    "圆圈：参考资料编号（[S1]–[S12]）",
    "带箭头的连线：参考资料 → 所属主题领域，箭头旁标注关系标签"
  ],
  "caption": "本图将研究资料包中的 12 条参考资料按安全主题域分类映射。左侧为设备层安全（硬件、通信、协议），右侧为平台与数据层安全（权限、AI、测试），从上到下覆盖从物理层到应用层的全栈。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
