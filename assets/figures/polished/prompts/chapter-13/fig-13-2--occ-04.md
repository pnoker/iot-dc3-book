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
  "id": "fig-13-2",
  "type": "flowchart",
  "title": "图13-2 数据上链流程图",
  "purpose": "展示从传感器采样到链上存证、链下存储、验证的完整流程，说明链下存储与链上指纹的协作关系。",
  "audience_takeaway": "读者应理解数据上链流程图中的主链路、责任边界和工程取舍。",
  "visual_focus": "从传感器到终点的主链路。",
  "layout": "自左向右的流程，传感器→边缘节点（聚合+哈希）→分支：左侧去往IPFS/Arweave（链下存储），右侧去往区块链（链上存证）→两侧再合并到验证方。",
  "components": [
    {
      "id": "r1",
      "label": "传感器",
      "type": "edge",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "r2",
      "label": "边缘节点：实线箭头，标注‘采样数据’",
      "type": "edge",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "r3",
      "label": "边缘节点",
      "type": "edge",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r4",
      "label": "IPFS/Arweave：实线箭头…",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r5",
      "label": "区块链：实线箭头，标注‘哈希+元数…",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "r6",
      "label": "IPFS/Arweave",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r7",
      "label": "验证方：实线箭头，标注‘提供原始数…",
      "type": "data",
      "group": "data_domain",
      "priority": "normal",
      "shape": "database"
    },
    {
      "id": "r8",
      "label": "区块链",
      "type": "platform",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "r9",
      "label": "验证方：实线箭头，标注‘查询哈希是…",
      "type": "decision",
      "group": "decision_domain",
      "priority": "normal",
      "shape": "decision"
    }
  ],
  "connections": [
    {
      "from": "r1",
      "to": "r2",
      "label": "传感器 → 边缘节点：实线箭头，标…",
      "style": "solid",
      "direction": "request"
    },
    {
      "from": "r3",
      "to": "ipfs_arweave",
      "label": "边缘节点 → IPFS/Arwea…",
      "style": "solid",
      "direction": "request"
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
      "id": "decision_domain",
      "label": "决策判断域",
      "role": "判断条件与分支边界"
    }
  ],
  "callouts": [
    "传感器 → 边缘节点：实线箭头，标注‘采样数据’",
    "边缘节点 → IPFS/Arweave：实线箭头，标注‘原始数据’",
    "边缘节点 → 区块链：实线箭头，标注‘哈希+元数据’"
  ],
  "legend": [
    "青绿色=设备/传感器；蓝色=核心处理逻辑；灰色=外部存储系统。",
    "实线箭头=同步/主动推送；虚线箭头=查询/读取。"
  ],
  "caption": "图13-2 展示数据从传感器采样到链下存储和链上存证，最终验证方通过两侧数据比对确认完整性的典型流程。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "决策节点必须写成可判断的问题或动作，分支标签保持短句。"
  ]
}
