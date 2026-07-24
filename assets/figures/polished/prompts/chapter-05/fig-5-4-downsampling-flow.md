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
  "id": "fig-5-4-downsampling-flow",
  "type": "dataflow",
  "title": "图5-4 降采样数据流程与数据量对比（假设场景）",
  "purpose": "展示原始高精度数据经过三级降采样后数据量显著减少，说明分层策略的压缩效果。",
  "audience_takeaway": "读者应理解降采样通过分层聚合将数据量逐步压缩，不同层服务于不同时效性需求。",
  "visual_focus": "从原始数据桶到天聚合桶的主链路，突出数据量呈量级缩减。",
  "layout": "从左至右的管道式数据流，包含原始数据桶、分钟聚合桶、小时聚合桶、天聚合桶，各桶下方标注相对数据量描述（如“原始数据量基准”、“显著减少”、“大幅降低”、“极小占比”）。",
  "components": [
    {
      "id": "c1",
      "label": "原始数据桶",
      "type": "data",
      "subtitle": "10秒级精度，短保留窗口",
      "group": "data_domain",
      "priority": "primary",
      "shape": "database"
    },
    {
      "id": "c2",
      "label": "分钟聚合桶",
      "type": "data",
      "subtitle": "每分钟均值，数据量显著减少",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "c3",
      "label": "小时聚合桶",
      "type": "data",
      "subtitle": "每小时均值，数据量大幅降低",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "c4",
      "label": "天聚合桶",
      "type": "data",
      "subtitle": "每天均值，数据量极小占比",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "CQ：每分钟聚合",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "CQ：每小时聚合",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c3",
      "to": "c4",
      "label": "CQ：每天聚合",
      "style": "solid",
      "direction": "left-to-right"
    }
  ],
  "regions": [
    {
      "id": "data_domain",
      "label": "数据资产域",
      "role": "数据沉淀与治理边界"
    }
  ],
  "callouts": [
    "“原始层”保留窗口通常按天计，用于故障回放；“分钟层”支撑短时趋势；“小时层”服务日报；“天层”服务年度趋势。"
  ],
  "legend": [
    "各桶数据量描述基于假设场景估算，实际项目因设备数、上报频率、字段数量而异。",
    "实线箭头：连续查询驱动自动化聚合。",
    "虚线箭头：应用层查询路径。"
  ],
  "caption": "图5-4 假设场景：中等规模工厂设备上报温度和湿度。三级降采样策略：原始数据保留短暂时间，分钟聚合保留中期，小时聚合保留季度级，天聚合保留年。各阶段数据量比例为基于常见压缩比的定性描述，非精确数值。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
