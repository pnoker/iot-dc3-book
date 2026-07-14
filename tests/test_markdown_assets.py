from __future__ import annotations

from core.markdown_assets import find_invalid_book_figures, parse_book_figure_payload


def test_book_figure_required_fields_accept_json_keys() -> None:
    markdown = '''```book-figure
{
  "id": "fig-01-01",
  "type": "layered",
  "title": "图1-1 平台分层架构",
  "purpose": "说明平台层次与职责边界。",
  "layout": "自下而上分层。",
  "elements": ["设备层", "平台层"],
  "relationships": ["设备层连接平台层"],
  "legend": ["蓝色=核心平台服务"],
  "caption": "图1-1 展示平台分层架构。",
  "render_notes": "HTML/SVG 统一绘制。"
}
```'''

    assert find_invalid_book_figures(markdown) == []


def test_book_figure_validation_normalizes_smart_quotes() -> None:
    markdown = '''```book-figure
id: “fig-01-01”
type: “flowchart”
title: “图1-1 数据处理流程”
purpose: “说明数据处理链路。”
layout: “从左到右流程。”
elements:
  - “采集”
  - “处理”
relationships:
  - “采集后进入处理”
legend:
  - “蓝色=流程节点”
caption: “图1-1 展示数据处理流程。”
render_notes: “HTML/SVG 统一绘制。”
```'''

    assert find_invalid_book_figures(markdown, allowed_types=["flowchart"]) == []


def test_book_figure_validation_rejects_unsupported_type() -> None:
    markdown = '''```book-figure
id: "fig-01-01"
type: "layered-architecture"
title: "图1-1 分层架构"
purpose: "说明层次。"
layout: "自下而上。"
elements:
  - "设备层"
relationships:
  - "设备层连接平台层"
legend:
  - "蓝色=平台"
caption: "图1-1 展示分层架构。"
render_notes: "HTML/SVG 统一绘制。"
```'''

    invalid = find_invalid_book_figures(markdown, allowed_types=["layered"])

    assert invalid == ["第1个 `book-figure` 不支持 type: layered-architecture；允许: layered"]


def test_book_figure_payload_preserves_structured_brief() -> None:
    body = '''id: "fig-02-01"
type: "architecture"
title: "图2-1 AIoT 平台分层架构"
purpose: "说明平台边界。"
audience_takeaway: "读者应理解设备、数据和智能决策之间的责任边界。"
visual_focus: "从设备接入到 Agent 编排的主链路。"
design_level: "logical"
layout: "自下而上分层。"
elements:
  - "设备与边缘"
relationships:
  - "设备接入平台"
regions:
  - id: "edge_domain"
    label: "设备与边缘域"
    role: "现场异构资源边界"
components:
  - id: "device_edge"
    label: "设备与边缘"
    type: "edge"
    subtitle: "传感器、PLC、网关"
    group: "edge_domain"
    priority: "normal"
    shape: "card"
  - id: "agent_orchestration"
    label: "Agent 编排"
    type: "ai"
    subtitle: "规则、模型、工具调用"
    group: "intelligence_domain"
    priority: "primary"
    shape: "card"
connections:
  - from: "device_edge"
    to: "agent_orchestration"
    label: "上下文供给"
    style: "dashed"
    direction: "event"
callouts:
  - "智能层不能绕过平台治理直接控制现场设备。"
legend:
  - "蓝色=平台；橙色=智能。"
caption: "图2-1 展示平台分层架构。"
visual_constraints:
  - "最多 6 个主节点。"
render_notes: "HTML/SVG 统一绘制。"'''

    payload, reason = parse_book_figure_payload(body)

    assert reason == ""
    assert payload is not None
    assert payload["components"][0]["id"] == "device_edge"
    assert payload["connections"][0]["from"] == "device_edge"


def test_book_figure_validation_rejects_placeholder_design_brief() -> None:
    markdown = '''```book-figure
id: "fig-13-08"
type: "flowchart"
title: "图13-8 判断框架"
purpose: "说明判断流程。"
layout: "从左到右。"
elements:
  - "节点1：判断是否需要跨组织共享；否→本地数据库；是→节点2。"
  - "节点2：判断是否需要防篡改存证；否→云服务；是→最右侧。"
relationships:
  - "节点1是→节点2；节点2是→最右侧；节点2否→传统云服务。"
legend:
  - "蓝色=平台"
caption: "图13-8 展示判断流程。"
render_notes: "HTML/SVG 统一绘制。"
```'''

    invalid = find_invalid_book_figures(markdown, allowed_types=["flowchart"])

    assert invalid
    assert "设计规格不达出版级" in invalid[0]
