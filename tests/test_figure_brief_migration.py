from __future__ import annotations

from core.figure_brief_migration import sync_chapter_figure_briefs_from_sections, upgrade_book_figure_briefs
from core.markdown_assets import find_invalid_book_figures, parse_book_figure_payload


def test_upgrade_book_figure_brief_adds_structured_fields() -> None:
    markdown = '''```book-figure
id: "fig-13-8"
type: "flowchart"
title: "图13-8 AIoT+区块链融合的工程判断框架"
purpose: "帮助架构师判断融合投入优先级。"
layout: "三个判断节点，每个节点引出分支决策。"
elements:
  - "节点1：‘数据是否需要跨组织共享？’——是/否分支。否→只需要物联网平台；是→进入节点2。"
  - "节点2：‘共享的数据是否需要防篡改存证？’——是/否分支。"
  - "最右侧：标记‘AIoT+区块链’融合推荐路径。"
relationships:
  - "节点1是→节点2；节点2是→最右侧路径。"
legend:
  - "蓝色=物联网基础设施层；橙色=AI智能决策层。"
caption: "图13-8 通过判断节点确定融合深度。"
render_notes: "标准流程图布局。"
```'''

    result = upgrade_book_figure_briefs(markdown)
    payload, reason = parse_book_figure_payload(result.markdown.split("```book-figure\n", 1)[1].rsplit("```", 1)[0])

    assert result.changed_blocks == 1
    assert reason == ""
    assert payload is not None
    assert payload["components"][0]["label"] == "数据是否需要跨组织共享？"
    assert payload["connections"][0]["from"] == "c1"
    assert find_invalid_book_figures(result.markdown) == []


def test_upgrade_nested_figure_json_unwraps_payload() -> None:
    markdown = '''```book-figure
{
  "figure": {
    "id": "fig-2-12",
    "type": "sequence_diagram",
    "title": "图2-12 Agentic 中心决策执行流程",
    "caption": "图2-12 Agentic 中心决策执行流程",
    "purpose": "展示 Agentic 中心处理任务时的关键交互序列。",
    "layout": {"orientation": "horizontal", "participants": [{"name": "用户/调度器", "role": "trigger"}, {"name": "Agentic 中心", "role": "orchestrator"}]},
    "elements": [{"type": "message", "from": "用户/调度器", "to": "Agentic 中心", "label": "指令", "arrow": "solid"}],
    "relationships": ["Agentic 中心接收用户指令。"],
    "legend": {"solid": "请求/命令"},
    "render_notes": {"format": "SVG"}
  }
}
```'''

    result = upgrade_book_figure_briefs(markdown)
    payload, _ = parse_book_figure_payload(result.markdown.split("```book-figure\n", 1)[1].rsplit("```", 1)[0])

    assert payload is not None
    assert payload["type"] == "sequence"
    assert payload["components"][0]["label"] == "用户/调度器"
    assert payload["connections"][0]["from"] == "p1"
    assert find_invalid_book_figures(result.markdown) == []


def test_upgrade_repairs_slug_prefixed_json_block() -> None:
    markdown = '''```book-figure
3-4-2-triangulation
{
  id: "3-4-2-triangulation",
  title: "三角测量定位原理示意",
  purpose: "说明三点定位的几何原理。",
  layout: "architecture",
  type: "architecture",
  elements: ["三个参考节点", "三个测距圆", "最优位置估计"],
  relationships: "参考节点通过测距形成位置估计；噪声产生交叠区域。",
  legend: ["●：参考节点"],
  caption: "图3-9 三角测量定位原理示意图。",
  render_notes: "绘制坐标网格与虚线圆。"
}
```'''

    result = upgrade_book_figure_briefs(markdown)

    assert result.failed_blocks == 0
    assert result.repaired_blocks == 1
    assert find_invalid_book_figures(result.markdown) == []


def test_upgrade_extracts_protocol_matrix_from_collapsed_layout() -> None:
    markdown = '''```book-figure
id: fig-9-7
type: layered_stack_3column
title: HTTP、MQTT、CoAP应用层协议角色对比
purpose: 展示三种协议在传输层、通信模型和典型场景上的差异。
layout: 三列水平排列，每列自顶向下分为三层“典型场景 → 通信模型 → 传输层”。
  - 左列（HTTP）：
    - 顶层（典型场景/浅蓝矩形块）：“设备配网”、“网关北向”
    - 中层（通信模型/浅绿矩形块）：“请求/响应”
    - 底层（传输层/浅黄矩形块）：“TCP + TLS”
  - 中列（MQTT）：
    - 顶层（典型场景/浅蓝矩形块）：“远程监控”、“双向指令”
    - 中层（通信模型/浅绿矩形块）：“发布/订阅（Broker中转）”
    - 底层（传输层/浅黄矩形块）：“TCP”
  - 右列（CoAP）：
    - 顶层（典型场景/浅蓝矩形块）：“传感器采集”、“状态上报”
    - 中层（通信模型/浅绿矩形块）：“请求/响应 + Observe”
    - 底层（传输层/浅黄矩形块）：“UDP + DTLS”
elements:
  - 设备供电特征说明。
relationships:
  - MQTT Broker 中转转发；HTTP 与 CoAP 点对点通信。
legend:
  - 浅蓝矩形块：典型场景
caption: HTTP、MQTT、CoAP 协议角色对比。
render_notes: 三列等宽矩阵布局。
```'''

    result = upgrade_book_figure_briefs(markdown)
    payload, _ = parse_book_figure_payload(result.markdown.split("```book-figure\n", 1)[1].rsplit("```", 1)[0])

    assert payload is not None
    assert payload["type"] == "matrix"
    assert len(payload["components"]) == 9
    assert payload["components"][0]["id"] == "http_scenario"
    assert payload["components"][4]["label"] == "发布/订阅（Broker中转）"
    assert {item["id"] for item in payload["regions"]} == {"protocol_http", "protocol_mqtt", "protocol_coap"}
    assert {item["from"] for item in payload["connections"]} >= {"http_transport", "mqtt_transport", "coap_transport", "mqtt_model"}
    assert find_invalid_book_figures(result.markdown) == []


def test_upgrade_extracts_relationship_endpoint_components() -> None:
    markdown = '''```book-figure
book-figure:
  id: "fig-11-3"
  type: "architecture"
  title: "智能路灯杆模块与边缘计算盒的数据流向"
  purpose: "展示传感器、边缘计算盒和云端服务的数据流。"
  layout: "纵向三层：挂载层、边缘计算层、云端层"
  elements:
    - name: "挂载层"
      description: "环境传感器组、AI摄像头、充电桩接入边缘计算盒。"
    - name: "边缘计算盒"
      description: "本地推理和协议转换。"
    - name: "云端层"
      description: "IoT Hub 与照明控制。"
  relationships:
    - from: "环境传感器组 -> 边缘计算盒"
      label: "Modbus RTU，1条/min"
      arrow_type: solid_green
    - from: "AI摄像头 -> 边缘计算盒"
      label: "RTSP，25fps（本地推理）"
      arrow_type: dashed_red
    - from: "边缘计算盒 -> IoT Hub"
      label: "MQTT，告警上报"
      arrow_type: solid_blue
    - from: "IoT Hub -> 照明控制"
      label: "CoAP，调光指令"
      arrow_type: solid_orange
    - from: "充电桩 <-> IoT Hub"
      label: "MQTT+TLS，计费数据"
      arrow_type: solid_purple_with_lock
  legend:
    - "绿色箭头：低频数据"
  caption: "智能路灯杆功能图。"
  render_notes: "三层之间用浅灰底区分。"
```'''

    result = upgrade_book_figure_briefs(markdown)
    payload, _ = parse_book_figure_payload(result.markdown.split("```book-figure\n", 1)[1].rsplit("```", 1)[0])

    assert payload is not None
    component_labels = {item["label"] for item in payload["components"]}
    component_ids = {item["id"] for item in payload["components"]}
    assert {"环境传感器组", "AI摄像头", "边缘计算盒", "IoT Hub", "照明控制", "充电桩"}.issubset(component_labels)
    assert len(payload["connections"]) == 5
    assert all(item["from"] in component_ids and item["to"] in component_ids for item in payload["connections"])
    assert any(item["style"] == "dashed" for item in payload["connections"])
    assert find_invalid_book_figures(result.markdown) == []


def test_upgrade_preserves_nested_layer_comparison_components() -> None:
    markdown = '''```book-figure
{
  "id": "fig-2-3",
  "type": "layered",
  "title": "五层架构模型与传统四层架构的对比示意",
  "purpose": "对比四层与五层架构。",
  "layout": "并排两列分层布局。",
  "elements": [
    {"side": "left", "layers": [{"name": "应用层"}, {"name": "平台层"}, {"name": "网络层"}, {"name": "感知层"}]},
    {"side": "right", "layers": [{"name": "应用层"}, {"name": "智能层（新增）"}, {"name": "平台层"}, {"name": "网络层"}, {"name": "感知层"}]}
  ],
  "relationships": [
    {"source": "四层-感知层", "target": "四层-应用层", "label": "数据流"},
    {"source": "五层-平台层", "target": "五层-智能层", "label": "读取数据与分析"},
    {"source": "五层-智能层", "target": "五层-平台层", "label": "命令下发"}
  ],
  "legend": ["实线箭头：数据流"],
  "caption": "五层架构模型与经典四层架构的对比。",
  "render_notes": "并排两列 SVG 渲染。"
}
```'''

    result = upgrade_book_figure_briefs(markdown)
    payload, _ = parse_book_figure_payload(result.markdown.split("```book-figure\n", 1)[1].rsplit("```", 1)[0])

    assert payload is not None
    assert len(payload["components"]) == 9
    assert payload["components"][5]["label"] == "五层-智能层（新增）"
    component_ids = {item["id"] for item in payload["components"]}
    assert all(item["from"] in component_ids and item["to"] in component_ids for item in payload["connections"])
    assert find_invalid_book_figures(result.markdown) == []


def test_sync_chapter_brief_uses_matching_section_brief() -> None:
    chapter_markdown = '''正文

```book-figure
id: fig-02-03
type: layered
title: 图2-3 五层架构模型与传统四层架构的对比示意
purpose: 对比四层和五层架构。
audience_takeaway: 读者理解主链路。
visual_focus: 两层简化图。
design_level: logical
layout: 分层布局。
elements:
- 右侧：数据经平台层向上进入智能层
relationships:
- 右侧 → 感知层
regions:
- id: platform_domain
  label: 平台服务域
  role: 核心服务能力边界
components:
- id: r1
  label: 右侧：数据经平台层向上进入智能层…
  type: platform
  subtitle: ''
  group: platform_domain
  priority: primary
  shape: card
- id: r2
  label: 感知层
  type: edge
  subtitle: ''
  group: edge_domain
  priority: normal
  shape: card
connections:
- from: r1
  to: r2
  label: 主链路
  style: solid
  direction: request
callouts:
- 简化图
legend:
- 蓝色=平台
caption: 图2-3 简化说明。
visual_constraints:
- 节点短标签。
render_notes: SVG。
```
'''
    section_markdown = '''小节

```book-figure
id: fig-2-3
type: layered
title: 五层架构模型与传统四层架构的对比示意
purpose: 对比四层和五层架构。
audience_takeaway: 读者理解主链路。
visual_focus: 四层与五层并列对比。
design_level: logical
layout: 并排两列分层布局。
elements:
- 四层-应用层
- 四层-平台层
- 四层-网络层
- 四层-感知层
- 五层-应用层
- 五层-智能层（新增）
- 五层-平台层
- 五层-网络层
- 五层-感知层
relationships:
- 四层-感知层 → 四层-应用层
regions:
- id: platform_domain
  label: 平台服务域
  role: 核心服务能力边界
components:
- id: r1
  label: 四层-应用层
  type: application
  subtitle: ''
  group: application_domain
  priority: normal
  shape: card
- id: r2
  label: 四层-平台层
  type: platform
  subtitle: ''
  group: platform_domain
  priority: normal
  shape: card
- id: r3
  label: 四层-网络层
  type: platform
  subtitle: ''
  group: platform_domain
  priority: normal
  shape: card
connections:
- from: r3
  to: r2
  label: 数据流
  style: solid
  direction: bottom-to-top
callouts:
- 四层与五层并列。
legend:
- 蓝色=平台
caption: 五层架构模型与经典四层架构的对比。
visual_constraints:
- 节点短标签。
render_notes: SVG。
```
'''

    result = sync_chapter_figure_briefs_from_sections(chapter_markdown, [section_markdown])
    payload, _ = parse_book_figure_payload(result.markdown.split("```book-figure\n", 1)[1].rsplit("```", 1)[0])

    assert result.changed_blocks == 1
    assert payload is not None
    assert payload["id"] == "fig-02-03"
    assert payload["title"] == "图2-3 五层架构模型与传统四层架构的对比示意"
    assert payload["components"][0]["label"] == "四层-应用层"


def test_sync_chapter_brief_prefers_title_over_conflicting_id() -> None:
    chapter_markdown = '''```book-figure
id: fig-11-4
type: architecture
title: 图11-4 智能路灯杆五类模块与边缘计算盒的数据流向（假设场景）
purpose: 展示路灯杆数据流。
audience_takeaway: 读者理解路灯杆模块。
visual_focus: 路灯杆到边缘盒。
design_level: logical
layout: 三层布局。
elements:
- 路灯杆
relationships:
- 路灯杆 → 边缘计算盒
regions: []
components:
- id: old
  label: 路灯杆
  type: edge
  subtitle: ''
  group: edge_domain
  priority: primary
  shape: card
connections: []
callouts: []
legend:
- 蓝色=平台
caption: 图11-4 智能路灯杆功能图。
visual_constraints:
- 节点短标签。
render_notes: SVG。
```'''
    city_section = '''```book-figure
id: fig-11-4
type: architecture
title: 图11-4 城市应急响应物联网架构
purpose: 展示城市应急。
audience_takeaway: 读者理解应急响应。
visual_focus: 应急响应。
design_level: logical
layout: 架构布局。
elements:
- 城市应急
relationships:
- 感知层 → 处理层
regions: []
components:
- id: city
  label: 城市应急
  type: platform
  subtitle: ''
  group: platform_domain
  priority: primary
  shape: card
connections: []
callouts: []
legend:
- 蓝色=平台
caption: 城市应急响应。
visual_constraints:
- 节点短标签。
render_notes: SVG。
```'''
    lamp_section = '''```book-figure
id: fig-11-3
type: architecture
title: 假设场景——智能路灯杆五类模块与边缘计算盒的数据流向
purpose: 展示路灯杆数据流。
audience_takeaway: 读者理解路灯杆模块。
visual_focus: 路灯杆到边缘盒。
design_level: logical
layout: 三层布局。
elements:
- 智能路灯杆
relationships:
- 环境传感器组 → 边缘计算盒
regions: []
components:
- id: sensor
  label: 环境传感器组
  type: edge
  subtitle: ''
  group: edge_domain
  priority: primary
  shape: card
- id: edge_box
  label: 边缘计算盒
  type: platform
  subtitle: ''
  group: platform_domain
  priority: normal
  shape: card
connections:
- from: sensor
  to: edge_box
  label: Modbus
  style: solid
  direction: request
callouts: []
legend:
- 蓝色=平台
caption: 智能路灯杆功能图。
visual_constraints:
- 节点短标签。
render_notes: SVG。
```'''

    result = sync_chapter_figure_briefs_from_sections(chapter_markdown, [city_section, lamp_section])
    payload, _ = parse_book_figure_payload(result.markdown.split("```book-figure\n", 1)[1].rsplit("```", 1)[0])

    assert payload is not None
    assert payload["id"] == "fig-11-4"
    assert payload["components"][0]["label"] == "环境传感器组"


def test_sync_chapter_brief_inserts_selected_figure_when_chapter_has_none() -> None:
    chapter_markdown = """## 9.1 协议体系总览

### 9.1.1 协议栈与分类

正文段落。
"""
    section_markdown = '''### 9.1.1 协议栈与分类

小节正文。

```book-figure
id: fig-9-1-1
type: architecture
title: 物联网协议栈与分类图
purpose: 展示协议栈层次。
audience_takeaway: 读者理解协议栈分层。
visual_focus: 感知设备到平台的协议链路。
design_level: logical
layout: 分层架构。
elements:
- 感知设备
- 网络传输
- 平台服务
relationships:
- 感知设备 → 网络传输
regions:
- id: platform_domain
  label: 平台服务域
  role: 协议汇聚边界
components:
- id: device
  label: 感知设备
  type: edge
  subtitle: ''
  group: edge_domain
  priority: primary
  shape: card
- id: network
  label: 网络传输
  type: platform
  subtitle: ''
  group: platform_domain
  priority: normal
  shape: card
connections:
- from: device
  to: network
  label: 协议承载
  style: solid
  direction: request
callouts:
- 协议选择影响功耗和可靠性。
legend:
- 蓝色=平台
caption: 物联网协议栈与分类图。
visual_constraints:
- 节点短标签。
render_notes: SVG。
```
'''

    result = sync_chapter_figure_briefs_from_sections(chapter_markdown, [section_markdown])

    assert result.inserted_blocks == 1
    assert result.changed_blocks == 1
    assert "### 9.1.1 协议栈与分类\n\n```book-figure" in result.markdown
    payload, _ = parse_book_figure_payload(result.markdown.split("```book-figure\n", 1)[1].rsplit("```", 1)[0])
    assert payload is not None
    assert payload["title"] == "物联网协议栈与分类图"
