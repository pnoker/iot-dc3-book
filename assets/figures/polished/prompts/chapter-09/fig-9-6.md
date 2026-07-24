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
  "id": "fig-9-6",
  "type": "architecture",
  "title": "图9-6 CoAP/LwM2M与NB-IoT协议协同架构",
  "purpose": "展示NB-IoT网络中应用层协议（LwM2M）、消息协议（CoAP）和无线接入层（NB-IoT）的分层堆叠关系，以及每层在共享停车位场景中的角色。",
  "audience_takeaway": "读者应理解CoAP/LwM2M与NB-IoT协议协同架构中的主链路、责任边界和工程取舍。",
  "visual_focus": "从上到下的主链路：LwM2M对象模型通过CoAP消息承载，CoAP消息封装于NB-IoT无线帧中。",
  "layout": "四个横向层叠矩形条，从上到下排列，每层之间用带箭头竖线连接，箭头指向上层，表示‘运行于之上’。左侧竖排小字标注标准组织，右侧竖排小字标注典型报文大小边界。",
  "components": [
    {
      "id": "business_app",
      "label": "业务应用",
      "type": "application",
      "subtitle": "停车管理、计费系统",
      "group": "app_layer",
      "priority": "normal",
      "shape": "card"
    },
    {
      "id": "lwm2m_client",
      "label": "LwM2M客户端",
      "type": "edge",
      "subtitle": "对象树、固件更新",
      "group": "mgmt_layer",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "coap_stack",
      "label": "CoAP栈",
      "type": "platform",
      "subtitle": "CON/NON消息、块传输",
      "group": "msg_layer",
      "priority": "primary",
      "shape": "bus"
    },
    {
      "id": "nb_iot_modem",
      "label": "NB-IoT模组",
      "type": "platform",
      "subtitle": "eDRX/PSM省电",
      "group": "access_layer",
      "priority": "primary",
      "shape": "card"
    }
  ],
  "connections": [
    {
      "from": "nb_iot_modem",
      "to": "coap_stack",
      "label": "承载无线帧",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "coap_stack",
      "to": "lwm2m_client",
      "label": "携带LwM2M消息",
      "style": "solid",
      "direction": "bottom-to-top"
    },
    {
      "from": "lwm2m_client",
      "to": "business_app",
      "label": "提供设备抽象",
      "style": "solid",
      "direction": "bottom-to-top"
    }
  ],
  "regions": [
    {
      "id": "app_layer",
      "label": "业务应用域",
      "role": "实现停车计费、设备状态监控等业务逻辑"
    },
    {
      "id": "mgmt_layer",
      "label": "设备管理层",
      "role": "抽象设备能力为对象树，管理固件和配置"
    },
    {
      "id": "msg_layer",
      "label": "消息传输层",
      "role": "提供轻量级、确认/非确认传输能力"
    },
    {
      "id": "access_layer",
      "label": "无线接入层",
      "role": "提供广覆盖、低功耗、高穿透的物理连接"
    }
  ],
  "callouts": [
    "NB-IoT的eDRX/PSM省电模式与LwM2M休眠调度配合，可显著延长电池更换周期。",
    "应用层协议从不单独工作，它与无线网络、设备管理模型形成合力。"
  ],
  "legend": [
    "中灰：业务应用层；浅青：设备管理层；浅蓝：消息传输层；深蓝：无线接入层。",
    "实线箭头表示‘承载/提供抽象’，方向从下到上。",
    "左侧标注标准组织，右侧标注典型报文大小边界。"
  ],
  "caption": "图9-6 CoAP/LwM2M与NB-IoT协议协同架构。左侧标注各层标准组织，右侧标注典型报文字节大小边界。底部加注‘假设场景：共享停车位地磁传感器，NON消息用于周期性上报，CON消息用于远程配置和固件升级’。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。",
    "优先表达边界和主链路，不把所有概念塞进一张图。"
  ]
}
