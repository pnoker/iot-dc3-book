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
  "type": "sequence",
  "title": "图13-2 设备DID注册与验证流程",
  "purpose": "展示从设备出厂、注册到被另一设备验证的完整身份生命周期。",
  "audience_takeaway": "读者应理解设备DID注册与验证流程中的主链路、责任边界和工程取舍。",
  "visual_focus": "从设备1内部到设备2→设备1的主链路。",
  "layout": "泳道从左至右依次为：设备1（身份主体）、智能合约（DeviceDIDRegistry，区块链上）、设备2（验证方）。",
  "components": [
    {
      "id": "c1",
      "label": "设备1内部",
      "type": "edge",
      "subtitle": "安全飞地生成ECDSA密钥对（私钥不可导出）",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "c2",
      "label": "设备1内部",
      "type": "edge",
      "subtitle": "根据公钥哈希构造DID字符串（例如 did:examp…",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c3",
      "label": "设备1→合约",
      "type": "edge",
      "subtitle": "发起 registerDevice(did, publ…",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c4",
      "label": "合约内部",
      "type": "platform",
      "subtitle": "验证签名，写入状态（owner, publicKeyH…",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c5",
      "label": "合约→区块链",
      "type": "platform",
      "subtitle": "日志 DIDRegistered 写入区块",
      "group": "platform_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c6",
      "label": "设备1→设备2",
      "type": "edge",
      "subtitle": "发送握手消息（包含DID + 随机挑战 + 对挑战的签…",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "bus"
    },
    {
      "id": "c7",
      "label": "设备2→合约",
      "type": "edge",
      "subtitle": "静态调用 didDocs[didHash] 查询DID…",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c8",
      "label": "合约→设备2",
      "type": "edge",
      "subtitle": "返回DID文档（owner, publicKeyHas…",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c9",
      "label": "设备2内部",
      "type": "edge",
      "subtitle": "检查 isActive",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "c10",
      "label": "设备2→设备1",
      "type": "edge",
      "subtitle": "返回验证结果（通过/失败）",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "步骤3、5、7为链上操作（虚线箭头…",
      "style": "dashed",
      "direction": "left-to-right"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "步骤3、5、7为链上操作（虚线箭头…",
      "style": "dashed",
      "direction": "left-to-right"
    },
    {
      "from": "c3",
      "to": "c4",
      "label": "步骤3、5、7为链上操作（虚线箭头…",
      "style": "dashed",
      "direction": "left-to-right"
    },
    {
      "from": "c4",
      "to": "c5",
      "label": "步骤3、5、7为链上操作（虚线箭头…",
      "style": "dashed",
      "direction": "left-to-right"
    },
    {
      "from": "c5",
      "to": "c6",
      "label": "步骤3、5、7为链上操作（虚线箭头…",
      "style": "dashed",
      "direction": "left-to-right"
    },
    {
      "from": "c6",
      "to": "c7",
      "label": "步骤3、5、7为链上操作（虚线箭头…",
      "style": "dashed",
      "direction": "left-to-right"
    },
    {
      "from": "c7",
      "to": "c8",
      "label": "步骤3、5、7为链上操作（虚线箭头…",
      "style": "dashed",
      "direction": "left-to-right"
    },
    {
      "from": "c8",
      "to": "c9",
      "label": "步骤3、5、7为链上操作（虚线箭头…",
      "style": "dashed",
      "direction": "left-to-right"
    },
    {
      "from": "c9",
      "to": "c10",
      "label": "步骤3、5、7为链上操作（虚线箭头…",
      "style": "dashed",
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
    }
  ],
  "callouts": [
    "步骤3、5、7为链上操作（虚线箭头），其余为链下操作（实线箭头）"
  ],
  "legend": [
    "实线箭头：链下通信，速度快，无gas消耗。",
    "虚线箭头：链上交易/查询，有gas成本和区块确认延迟。"
  ],
  "caption": "图13-2 展示设备从硬件密钥生成、DID注册到验证方自主验证的完整身份生命周期。链上操作以虚线区分。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
