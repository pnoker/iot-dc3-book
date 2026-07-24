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
  "id": "fig-9-3-lwm2m-stack",
  "type": "architecture",
  "title": "图 9-3 LwM2M 协议栈与逻辑实体交互架构",
  "purpose": "直观展示 LwM2M 在协议栈中的位置（CoAP之上、UDP/DTLS之上、无线接入网之上）以及三大逻辑实体（Bootstrap Server、LwM2M Server、LwM2M Client）之间的四种核心交互流程，帮助读者建立从底层传输到上层设备管理的完整视图。",
  "audience_takeaway": "读者应理解该架构中的主链路、责任边界和工程取舍。",
  "visual_focus": "从引导流程到观察通知流程的主链路，以及 Client 内部对象树的展开。",
  "layout": "左侧为 Client 实体（含对象树层级展开），右侧上下排列 Bootstrap Server 和 LwM2M Server；底部用分层条带表示协议栈（无线接入→UDP/DTLS→CoAP）；Client 与 Server 之间用一条竖直虚线表示公网/无线接入边界。",
  "components": [
    {
      "id": "c1",
      "label": "Bootstrap Server",
      "type": "platform",
      "subtitle": "引导服务器",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "c2",
      "label": "LwM2M Server",
      "type": "platform",
      "subtitle": "管理服务器",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "c3",
      "label": "LwM2M Client",
      "type": "edge",
      "subtitle": "设备端",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "c4",
      "label": "Protocol Stack",
      "type": "platform",
      "subtitle": "传输层（NB-IoT/5G/LoRaWAN + UDP/DTLS + CoAP）",
      "priority": "normal",
      "shape": "bus"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c3",
      "label": "引导配置",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c3",
      "to": "c2",
      "label": "注册/更新",
      "style": "solid",
      "direction": "right-to-left"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "观察/读写/升级",
      "style": "dashed",
      "direction": "left-to-right"
    },
    {
      "from": "c3",
      "to": "c2",
      "label": "通知/响应",
      "style": "solid",
      "direction": "right-to-left"
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
    "对象树的标准化使得不同厂商的设备共享同一套读写接口。",
    "引导服务器仅在首次或重置时介入，正常运行时设备直接与 LwM2M Server 交互。"
  ],
  "legend": [
    "蓝色 = 平台侧实体；青绿色 = 设备侧实体；灰色 = 协议栈底座。",
    "实线 = 同步请求/响应；虚线 = 观察/异步推送。"
  ],
  "caption": "图 9-3 展示 LwM2M 协议栈层次以及三大实体之间的引导、注册、观察/通知、读写/配置、固件升级五种交互流程。",
  "visual_constraints": [
    "最多 4 个主节点，节点标签短，解释放入 callouts。",
    "图例放在图底部，不遮挡分组边界。",
    "橙色不用于此图，仅在 AI 相关章节使用。"
  ]
}
