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
  "id": "fig-6-6",
  "type": "layered",
  "title": "图6-6 物联网微服务容器部署的端-边-云分层架构",
  "purpose": "展示从端设备、边缘节点到云端的数据流与控制流，以及各层使用的容器编排工具",
  "audience_takeaway": "读者应理解物联网微服务容器部署的端-边-云分层架构中的主链路、责任边界和工程取舍。",
  "visual_focus": "从云端层到端设备层的主链路。",
  "layout": "自下而上三层架构：端设备层 → 边缘计算层 → 云端中心层",
  "components": [
    {
      "id": "c1",
      "label": "云端层",
      "type": "platform",
      "subtitle": "完整 Kubernetes 集群，包含控制平面（API…",
      "group": "platform_domain",
      "priority": "primary",
      "shape": "card"
    },
    {
      "id": "c2",
      "label": "边缘层",
      "type": "edge",
      "subtitle": "节点内包含：边缘网关 Pod、协议适配 Pod（Mod…",
      "group": "edge_domain",
      "priority": "primary",
      "shape": "bus"
    },
    {
      "id": "c3",
      "label": "端设备层",
      "type": "edge",
      "subtitle": "传感器、PLC、执行器，通过现场总线（Modbus R…",
      "group": "edge_domain",
      "priority": "normal",
      "shape": "bus"
    }
  ],
  "connections": [
    {
      "from": "c1",
      "to": "c2",
      "label": "云端中心服务通过 MQTT Bro…",
      "style": "solid",
      "direction": "left-to-right"
    },
    {
      "from": "c2",
      "to": "c3",
      "label": "边缘节点与端设备之间采用实时采集/…",
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
      "id": "edge_domain",
      "label": "设备与边缘域",
      "role": "现场异构资源边界"
    }
  ],
  "callouts": [
    "云端中心服务通过 MQTT Broker 与边缘网关异步交换数据，实线双向箭头",
    "边缘节点与端设备之间采用实时采集/控制回路，不经过云端，实线双向箭头",
    "边缘运行时与云端同步可采用 gRPC 或 MQTT QoS 1，虚线箭头"
  ],
  "legend": [
    "蓝色=核心平台中心服务；青绿色=边缘计算与设备接入；灰色=端设备与现场总线",
    "实线箭头=同步调用或强依赖；虚线箭头=异步消息或可选同步"
  ],
  "caption": "图6-6 展示物联网微服务从端设备到边缘节点再到云端的容器部署分层架构。边缘层运行 k3s 轻量集群处理协议适配和本地缓存，云端运行完整 K8s 集群承载中心服务。",
  "visual_constraints": [
    "节点标签使用短名词短语，解释性文字放入 callouts 或正文。",
    "图例放在底部，不遮挡主体结构。"
  ]
}
