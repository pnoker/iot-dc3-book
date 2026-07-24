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
  "id": "table-3-8-1",
  "type": "matrix",
  "title": "感知层技术工程检查清单",
  "purpose": "提供覆盖传感器、RFID、定位、边缘计算、端侧AI和物模型六大领域的12个关键检查项，帮助工程师在不同项目阶段进行系统性自我审核，减少现场部署问题。",
  "audience_takeaway": "读者应理解感知层技术工程检查清单中的主链路、责任边界和工程取舍。",
  "visual_focus": "从传感器选型到自适应采样的主链路。",
  "layout": "行列表，共12行，每行包含“领域”“检查项”“自检说明”三列。",
  "components": [
    {
      "id": "c1",
      "label": "传感器选型",
      "type": "edge",
      "subtitle": "对照物理量范围预留余量，避免非线性偏移",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "c2",
      "label": "传感器接口",
      "type": "edge",
      "subtitle": "模拟信号需考虑ADC精度与屏蔽；数字接口注意地…",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c3",
      "label": "信号调理",
      "type": "platform",
      "subtitle": "快速变化信号需高采样率；关注噪声等效位宽",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c4",
      "label": "RFID频段选择",
      "type": "platform",
      "subtitle": "金属和液体环境不适合UHF；有源标签需评估电池…",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c5",
      "label": "防碰撞协议",
      "type": "platform",
      "subtitle": "大批量读写需评估Q算法或改进型帧时隙ALOHA…",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c6",
      "label": "定位技术融合",
      "type": "platform",
      "subtitle": "单源技术有盲区，需设计降级方案；卡尔曼滤波初始…",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c7",
      "label": "边缘节点硬件",
      "type": "edge",
      "subtitle": "不只关注CPU主频，需评估NPU或DSP可用性…",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c8",
      "label": "数据预处理",
      "type": "data",
      "subtitle": "滑动平均有相位延迟；实时场景优先用卡尔曼滤波",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "c9",
      "label": "端侧AI部署",
      "type": "ai",
      "subtitle": "从float32转int8需使用校准集，避免精…",
      "group": "intelligence_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c10",
      "label": "自适应采样",
      "type": "data",
      "subtitle": "阈值太小功耗大，太大漏事件，需统计历史数据确定…",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "无（独立表格，无元素间关系）",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "无（独立表格，无元素间关系）",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c3",
      "to": "c4",
      "label": "无（独立表格，无元素间关系）",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c4",
      "to": "c5",
      "label": "无（独立表格，无元素间关系）",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c5",
      "to": "c6",
      "label": "无（独立表格，无元素间关系）",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c6",
      "to": "c7",
      "label": "无（独立表格，无元素间关系）",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c7",
      "to": "c8",
      "label": "无（独立表格，无元素间关系）",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c8",
      "to": "c9",
      "label": "无（独立表格，无元素间关系）",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c9",
      "to": "c10",
      "label": "无（独立表格，无元素间关系）",
      "style": "solid",
      "direction": "left-to-right"
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
    "无（独立表格，无元素间关系）"
  ],
  "legend": [
    "无"
  ],
  "caption": "表3-8-1 感知层技术工程检查清单",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
