from __future__ import annotations

import html
import json
import math
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from core.figures import FigureSpec, render_svg_to_png, scan_figure_specs
from core.workflow import BookProject

WIDTH = 1200
HEIGHT = 760
FONT = "'JetBrains Mono', 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif"

PALETTE = {
    "bg": "#FFFFFF",
    "ink": "#0F172A",
    "muted": "#64748B",
    "subtle": "#94A3B8",
    "line": "#CBD5E1",
    "border": "#E2E8F0",
    "panel": "#F8FAFC",
    "panel2": "#F1F5F9",
    "edge": "#22D3EE",
    "edge_fill": "#ECFEFF",
    "platform": "#34D399",
    "platform_fill": "#ECFDF5",
    "data": "#A78BFA",
    "data_fill": "#F5F3FF",
    "application": "#FBBF24",
    "application_fill": "#FFF7ED",
    "security": "#FB7185",
    "security_fill": "#FFF1F2",
    "ai": "#FB923C",
    "ai_fill": "#FFF7ED",
    "neutral": "#94A3B8",
    "neutral_fill": "#F8FAFC",
}

GROUP_ORDER = [
    "application_domain",
    "edge_domain",
    "platform_domain",
    "data_domain",
    "security_domain",
    "external_domain",
]

GROUP_LABELS = {
    "application_domain": "应用 / 用户",
    "edge_domain": "设备 / 边缘",
    "platform_domain": "平台 / 服务",
    "data_domain": "数据 / 存储",
    "security_domain": "安全 / 治理",
    "external_domain": "外部系统",
    "default": "核心能力",
}


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def clean_text(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = text.replace("‘", "").replace("’", "").replace("“", "").replace("”", "")
    text = re.sub(
        r"[（(][^）)]*(?:最左|左中|右中|最右|蓝色|青色|绿色|橙色|紫色|灰色|节点|图标|实线|虚线|箭头|标注|使用|内部包含)[^）)]*[）)]",
        "",
        text,
    )
    text = re.sub(r"[（(]\s*[）)]", "", text)
    for sep in ("：", ":"):
        if sep in text:
            prefix, suffix = text.split(sep, 1)
            if 2 <= len(prefix.strip()) <= 18:
                text = prefix
            elif suffix.strip():
                text = suffix
            break
    text = re.sub(r"(?:，|,)?\s*(?:实线|虚线)?箭头.*$", "", text)
    text = re.sub(r"\s+", " ", text).strip(" ，。；;：:")
    return text


def compact(value: object, limit: int = 24) -> str:
    text = clean_text(value)
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip(" ，。；;、") + "…"


def visual_width(text: str) -> float:
    width = 0.0
    for char in text:
        width += 1.0 if ord(char) > 127 else 0.58
    return width


def wrap_text(value: object, max_units: float, max_lines: int) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    lines: list[str] = []
    current = ""
    current_units = 0.0
    for char in text:
        char_units = 1.0 if ord(char) > 127 else 0.58
        if current and current_units + char_units > max_units:
            lines.append(current.rstrip())
            current = char
            current_units = char_units
            if len(lines) >= max_lines:
                break
        else:
            current += char
            current_units += char_units
    if len(lines) < max_lines and current:
        lines.append(current.rstrip())
    remainder_units = visual_width(text) - sum(visual_width(line) for line in lines)
    if remainder_units > 0.5 and lines:
        lines[-1] = lines[-1].rstrip(" ，。；;、") + "…"
    return lines[:max_lines]


def text_block(
    value: object,
    x: float,
    y: float,
    width: float,
    *,
    size: int = 14,
    fill: str = PALETTE["ink"],
    weight: int = 500,
    anchor: str = "start",
    max_lines: int = 2,
    line_gap: int = 5,
) -> str:
    max_units = max(4.0, width / (size * 0.96))
    lines = wrap_text(value, max_units, max_lines)
    parts = []
    for index, line in enumerate(lines):
        parts.append(
            f'<text x="{x:.1f}" y="{y + index * (size + line_gap):.1f}" fill="{fill}" '
            f'font-size="{size}" font-family="{FONT}" font-weight="{weight}" '
            f'text-anchor="{anchor}">{esc(line)}</text>'
        )
    return "\n".join(parts)


def normalize_nodes(spec: FigureSpec, max_nodes: int = 12) -> list[dict[str, str]]:
    raw_nodes: list[dict[str, Any]] = list(spec.components or [])
    if not raw_nodes:
        raw_nodes = [
            {"id": f"n{index}", "label": item, "type": "external", "group": "external_domain"}
            for index, item in enumerate(spec.elements or [spec.title], start=1)
        ]
    nodes: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_nodes[:max_nodes], start=1):
        base_id = str(raw.get("id") or f"n{index}").strip() or f"n{index}"
        node_id = base_id if base_id not in seen else f"{base_id}_{index}"
        seen.add(node_id)
        node_type = str(raw.get("type") or raw.get("shape") or "external")
        group = str(raw.get("group") or infer_group(node_type, raw.get("label") or ""))
        nodes.append(
            {
                "id": node_id,
                "label": compact(raw.get("label") or raw.get("title") or base_id, 28),
                "subtitle": compact(raw.get("subtitle") or raw.get("role") or raw.get("description") or "", 42),
                "type": node_type,
                "group": group,
                "priority": str(raw.get("priority") or "normal"),
                "shape": str(raw.get("shape") or "card"),
            }
        )
    return nodes


def infer_group(node_type: str, label: object) -> str:
    raw = f"{node_type} {label}".lower()
    if any(token in raw for token in ["app", "application", "user", "用户", "应用", "业务", "可视化"]):
        return "application_domain"
    if any(token in raw for token in ["edge", "device", "sensor", "gateway", "设备", "传感", "网关", "边缘", "终端"]):
        return "edge_domain"
    if any(token in raw for token in ["data", "database", "storage", "cache", "数据", "存储", "缓存", "数据库", "队列"]):
        return "data_domain"
    if any(token in raw for token in ["security", "auth", "safe", "安全", "鉴权", "权限"]):
        return "security_domain"
    if any(token in raw for token in ["service", "platform", "process", "服务", "平台", "中心", "引擎"]):
        return "platform_domain"
    return "external_domain"


def normalize_edges(spec: FigureSpec, nodes: list[dict[str, str]], max_edges: int = 14) -> list[dict[str, str]]:
    node_ids = {node["id"] for node in nodes}
    edges: list[dict[str, str]] = []
    for raw in spec.connections[:max_edges]:
        source = str(raw.get("from") or "")
        target = str(raw.get("to") or "")
        if source in node_ids and target in node_ids and source != target:
            edges.append(
                {
                    "from": source,
                    "to": target,
                    "label": compact(raw.get("label") or "", 22),
                    "style": str(raw.get("style") or "solid"),
                    "direction": str(raw.get("direction") or ""),
                }
            )
    if not edges and len(nodes) > 1:
        edges = [
            {"from": nodes[index]["id"], "to": nodes[index + 1]["id"], "label": "", "style": "solid", "direction": ""}
            for index in range(len(nodes) - 1)
        ]
    return edges


def color_key(node: dict[str, str]) -> str:
    raw = " ".join([node.get("type", ""), node.get("group", ""), node.get("label", ""), node.get("subtitle", "")]).lower()
    if any(token in raw for token in ["安全", "鉴权", "权限", "security", "auth"]):
        return "security"
    if any(token in raw for token in ["数据", "库", "缓存", "存储", "队列", "data", "database", "storage", "cache"]):
        return "data"
    if any(token in raw for token in ["设备", "传感", "网关", "边缘", "终端", "edge", "device", "sensor", "gateway"]):
        return "edge"
    if any(token in raw for token in ["应用", "用户", "业务", "大屏", "app", "application", "user"]):
        return "application"
    if any(token in raw for token in ["模型", "智能", "model", "agent"]):
        return "ai"
    if any(token in raw for token in ["平台", "服务", "中心", "引擎", "platform", "service", "process"]):
        return "platform"
    return "neutral"


def node_colors(node: dict[str, str]) -> tuple[str, str]:
    key = color_key(node)
    return PALETTE[f"{key}_fill"], PALETTE[key]


def rect(
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    fill: str,
    stroke: str,
    rx: float = 6,
    sw: float = 1.5,
    dash: str = "",
) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx:.1f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw:.1f}"{dash_attr}/>'
    )


def card(x: float, y: float, w: float, h: float, node: dict[str, str], *, index: int | None = None) -> str:
    fill, stroke = node_colors(node)
    compact_card = h < 58
    title_size = 12 if compact_card else 13 if h < 78 else 14
    subtitle_size = 8 if compact_card else 9 if h < 78 else 10
    text_width = w - 20
    title_lines = wrap_text(node["label"], max(4.0, text_width / (title_size * 0.9)), 1 if compact_card else 2)
    subtitle_lines = [] if compact_card or not node.get("subtitle") else wrap_text(node["subtitle"], max(4.0, text_width / (subtitle_size * 0.9)), 1)
    title_block_height = len(title_lines) * title_size + max(0, len(title_lines) - 1) * 4
    subtitle_block_height = len(subtitle_lines) * subtitle_size if subtitle_lines else 0
    gap = 5 if title_lines and subtitle_lines else 0
    total_text_height = title_block_height + gap + subtitle_block_height
    first_title_y = y + (h - total_text_height) / 2 + title_size
    parts = [rect(x, y, w, h, fill=fill, stroke=stroke, rx=6, sw=1.5)]
    if index is not None and h >= 64:
        parts.append(f'<text x="{x + 10:.1f}" y="{y + 16:.1f}" fill="{stroke}" font-size="8" font-family="{FONT}" font-weight="700">{index:02d}</text>')
    for line_index, line in enumerate(title_lines):
        parts.append(
            f'<text x="{x + w / 2:.1f}" y="{first_title_y + line_index * (title_size + 4):.1f}" '
            f'fill="{PALETTE["ink"]}" font-size="{title_size}" font-family="{FONT}" font-weight="700" '
            f'text-anchor="middle">{esc(line)}</text>'
        )
    if subtitle_lines:
        subtitle_y = first_title_y + title_block_height + gap
        parts.append(
            f'<text x="{x + w / 2:.1f}" y="{subtitle_y:.1f}" fill="{PALETTE["muted"]}" '
            f'font-size="{subtitle_size}" font-family="{FONT}" font-weight="500" text-anchor="middle">'
            f'{esc(subtitle_lines[0])}</text>'
        )
    return "\n".join(parts)


def center(box: tuple[float, float, float, float]) -> tuple[float, float]:
    x, y, w, h = box
    return x + w / 2, y + h / 2


def connection_points(
    source: tuple[float, float, float, float],
    target: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    sx, sy = center(source)
    tx, ty = center(target)
    x, y, w, h = source
    tx0, ty0, tw, th = target
    dx = tx - sx
    dy = ty - sy
    if abs(dx) >= abs(dy):
        start_x = x + w if dx >= 0 else x
        start_y = sy
        end_x = tx0 if dx >= 0 else tx0 + tw
        end_y = ty
    else:
        start_x = sx
        start_y = y + h if dy >= 0 else y
        end_x = tx
        end_y = ty0 if dy >= 0 else ty0 + th
    return start_x, start_y, end_x, end_y


def edge_svg(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    label: str = "",
    *,
    dashed: bool = False,
    color: str = PALETTE["neutral"],
    curve: bool = True,
) -> tuple[str, str]:
    dash = ' stroke-dasharray="4 4"' if dashed else ""
    if curve and abs(x2 - x1) > 40 and abs(y2 - y1) > 40:
        mid_x = (x1 + x2) / 2
        path = f'M {x1:.1f} {y1:.1f} L {mid_x:.1f} {y1:.1f} L {mid_x:.1f} {y2:.1f} L {x2:.1f} {y2:.1f}'
        line = f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.5"{dash} marker-end="url(#arrowhead)"/>'
    else:
        line = (
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{color}" stroke-width="1.5"{dash} marker-end="url(#arrowhead)"/>'
        )
    label_svg = ""
    if label:
        label_text = compact(label, 16)
        label_units = max(visual_width(label_text), 4)
        label_w = min(170, label_units * 8.1 + 18)
        lx = (x1 + x2) / 2 - label_w / 2
        ly = (y1 + y2) / 2 - 13
        label_svg = "\n".join(
            [
                rect(lx, ly, label_w, 24, fill="#FFFFFF", stroke="#E5E7EB", rx=6, sw=1.0),
                text_block(label_text, lx + label_w / 2, ly + 16, label_w - 12, size=10, fill=PALETTE["muted"], weight=500, anchor="middle", max_lines=1),
            ]
        )
    return line, label_svg


def render_edge_set(edges: list[dict[str, str]], positions: dict[str, tuple[float, float, float, float]], *, max_labels: int = 7) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    labels: list[str] = []
    for index, edge in enumerate(edges):
        if edge["from"] not in positions or edge["to"] not in positions:
            continue
        x1, y1, x2, y2 = connection_points(positions[edge["from"]], positions[edge["to"]])
        line, label = edge_svg(
            x1,
            y1,
            x2,
            y2,
            edge["label"] if index < max_labels else "",
            dashed=edge.get("style") == "dashed",
        )
        lines.append(line)
        if label:
            labels.append(label)
    return lines, labels


def header_svg(spec: FigureSpec) -> str:
    title = compact(spec.title, 46)
    subtitle = compact(spec.audience_takeaway or spec.purpose or spec.visual_focus or spec.caption, 82)
    figure_type = spec.figure_type.upper()
    parts = [
        f'<circle cx="64" cy="40" r="6" fill="{PALETTE["edge"]}"/>',
        f'<text x="82" y="48" fill="{PALETTE["ink"]}" font-size="22" font-family="{FONT}" font-weight="700">{esc(title)}</text>',
        text_block(subtitle, 82, 78, 820, size=12, fill=PALETTE["muted"], weight=500, max_lines=1),
        rect(1008, 30, 132, 32, fill="#FFFFFF", stroke=PALETTE["border"], rx=6, sw=1.2),
        f'<text x="1074" y="51" fill="{PALETTE["muted"]}" font-size="11" font-family="{FONT}" font-weight="700" text-anchor="middle">{esc(figure_type)}</text>',
        f'<line x1="58" y1="103" x2="1142" y2="103" stroke="{PALETTE["line"]}" stroke-width="1"/>',
    ]
    return "\n".join(parts)


def legend_svg(spec: FigureSpec, nodes: list[dict[str, str]]) -> str:
    seen: list[tuple[str, str]] = []
    for node in nodes:
        key = color_key(node)
        label = {
            "edge": "设备/边缘",
            "platform": "平台服务",
            "data": "数据存储",
            "application": "应用用户",
            "security": "安全治理",
            "ai": "智能模型",
            "neutral": "辅助系统",
        }[key]
        if all(existing_label != label for existing_label, _ in seen):
            seen.append((label, PALETTE[key]))
    items = seen[:5]
    parts = [f'<line x1="58" y1="675" x2="1142" y2="675" stroke="{PALETTE["line"]}" stroke-width="1"/>']
    x = 66
    y = 708
    for item, color in items[:5]:
        if x > 1040:
            break
        parts.append(f'<circle cx="{x:.1f}" cy="{y - 4:.1f}" r="4" fill="{color}"/>')
        parts.append(text_block(item, x + 14, y, 150, size=11, fill=PALETTE["muted"], weight=600, max_lines=1))
        x += 168
    return "\n".join(parts)


def shell(spec: FigureSpec, body: str, nodes: list[dict[str, str]]) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{esc(spec.title)}" data-style="architecture-diagram-white-book">
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="{PALETTE['muted']}"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" fill="{PALETTE['bg']}"/>
  {header_svg(spec)}
  {body}
  {legend_svg(spec, nodes)}
</svg>'''


def render_architecture(spec: FigureSpec, nodes: list[dict[str, str]], edges: list[dict[str, str]]) -> str:
    grouped: dict[str, list[dict[str, str]]] = {}
    for node in nodes:
        grouped.setdefault(node.get("group") or "default", []).append(node)
    group_keys = [key for key in GROUP_ORDER if key in grouped]
    group_keys.extend(key for key in grouped if key not in group_keys)
    if not group_keys:
        group_keys = ["default"]
        grouped["default"] = nodes
    if len(group_keys) > 5:
        group_keys = [*group_keys[:4], "default"]
        grouped["default"] = [node for key, values in grouped.items() if key not in group_keys[:4] for node in values]

    panel_y = 132
    panel_h = 512
    gap = 34
    left = 58
    total_w = 1084
    col_w = (total_w - gap * (len(group_keys) - 1)) / len(group_keys)
    positions: dict[str, tuple[float, float, float, float]] = {}
    group_bounds: dict[str, tuple[float, float, float, float]] = {}
    node_to_group: dict[str, str] = {}
    parts: list[str] = []
    connector_parts: list[str] = []
    for col, group_key in enumerate(group_keys):
        x = left + col * (col_w + gap)
        group_nodes = grouped[group_key]
        group_bounds[group_key] = (x, panel_y, col_w, panel_h)
        parts.append(rect(x, panel_y, col_w, panel_h, fill="#FFFFFF", stroke=PALETTE["line"], rx=12, sw=1.2, dash="8 4"))
        parts.append(text_block(GROUP_LABELS.get(group_key, GROUP_LABELS["default"]), x + 18, panel_y + 29, col_w - 36, size=12, fill=PALETTE["muted"], weight=700, max_lines=1))
        parts.append(f'<line x1="{x + 18:.1f}" y1="{panel_y + 46:.1f}" x2="{x + col_w - 18:.1f}" y2="{panel_y + 46:.1f}" stroke="{PALETTE["line"]}" stroke-width="1"/>')
        count = max(1, len(group_nodes))
        card_gap = 14
        card_h = min(68, max(50, (panel_h - 72 - card_gap * (count - 1)) / count))
        card_w = col_w - 34
        start_y = panel_y + 62 + max(0, (panel_h - 72 - count * card_h - (count - 1) * card_gap) / 2)
        for index, node in enumerate(group_nodes):
            y = start_y + index * (card_h + card_gap)
            positions[node["id"]] = (x + 17, y, card_w, card_h)
            node_to_group[node["id"]] = group_key
            if index > 0:
                previous = group_nodes[index - 1]
                prev_box = positions[previous["id"]]
                curr_box = positions[node["id"]]
                x1, y1 = prev_box[0] + prev_box[2] / 2, prev_box[1] + prev_box[3]
                x2, y2 = curr_box[0] + curr_box[2] / 2, curr_box[1]
                line, _ = edge_svg(x1, y1 + 2, x2, y2 - 2, "", dashed=False, curve=False)
                connector_parts.append(line)

    bridge_arrows: list[str] = []
    bridge_seen: set[tuple[int, int, int]] = set()
    bridge_lanes: dict[tuple[int, int], int] = {}
    group_index = {group_key: index for index, group_key in enumerate(group_keys)}
    for edge in edges:
        source_group = node_to_group.get(edge["from"])
        target_group = node_to_group.get(edge["to"])
        if source_group is None or target_group is None or source_group == target_group:
            continue
        source_index = group_index[source_group]
        target_index = group_index[target_group]
        direction = 1 if target_index > source_index else -1
        start = min(source_index, target_index)
        end = max(source_index, target_index)
        for index in range(start, end):
            lane_key = (index, index + 1)
            lane = bridge_lanes.get(lane_key, 0)
            bridge_lanes[lane_key] = (lane + 1) % 4
            marker = (index, index + 1, direction * (lane + 1))
            if marker in bridge_seen:
                continue
            bridge_seen.add(marker)
            left_group = group_keys[index]
            right_group = group_keys[index + 1]
            left_box = group_bounds[left_group]
            right_box = group_bounds[right_group]
            y = panel_y + 86 + lane * 34
            if direction > 0:
                x1 = left_box[0] + left_box[2] + 5
                x2 = right_box[0] - 5
            else:
                x1 = right_box[0] - 5
                x2 = left_box[0] + left_box[2] + 5
            line, _ = edge_svg(x1, y, x2, y, "", dashed=edge.get("style") == "dashed", curve=False)
            bridge_arrows.append(line)

    node_parts = [card(*positions[node["id"]], node) for node in nodes if node["id"] in positions]
    return "\n".join(parts + bridge_arrows + connector_parts + node_parts)


def render_layered(spec: FigureSpec, nodes: list[dict[str, str]], edges: list[dict[str, str]]) -> str:
    count = max(1, len(nodes))
    left = 105
    top = 138
    width = 990
    gap = 14
    layer_h = min(78, max(54, (510 - gap * (count - 1)) / count))
    positions: dict[str, tuple[float, float, float, float]] = {}
    parts: list[str] = [rect(left - 24, top - 24, width + 48, 560, fill="#FFFFFF", stroke=PALETTE["line"], rx=12, sw=1.2, dash="8 4")]
    connector_parts: list[str] = []
    node_parts: list[str] = []
    for index, node in enumerate(nodes):
        y = top + index * (layer_h + gap)
        positions[node["id"]] = (left, y, width, layer_h)
        node_parts.append(card(left, y, width, layer_h, node, index=index + 1))
        if index < len(nodes) - 1:
            x1, y1 = left + width / 2, y + layer_h
            x2, y2 = left + width / 2, y + layer_h + gap - 2
            line, _ = edge_svg(x1, y1 + 2, x2, y2, "", dashed=False, curve=False)
            connector_parts.append(line)
    return "\n".join(parts + connector_parts + node_parts)


def render_timeline(spec: FigureSpec, nodes: list[dict[str, str]], edges: list[dict[str, str]]) -> str:
    count = max(1, len(nodes))
    start_x = 100
    end_x = 1100
    axis_y = 376
    step = 0 if count == 1 else (end_x - start_x) / (count - 1)
    parts = [
        f'<line x1="{start_x}" y1="{axis_y}" x2="{end_x}" y2="{axis_y}" stroke="{PALETTE["muted"]}" stroke-width="1.8" marker-end="url(#arrowhead)"/>'
    ]
    for index, node in enumerate(nodes):
        x = start_x + index * step
        _, stroke = node_colors(node)
        parts.append(f'<circle cx="{x:.1f}" cy="{axis_y:.1f}" r="12" fill="#FFFFFF" stroke="{stroke}" stroke-width="1.8"/>')
        parts.append(f'<circle cx="{x:.1f}" cy="{axis_y:.1f}" r="5" fill="{stroke}"/>')
        card_w = 210
        card_h = 78
        y = axis_y - 135 if index % 2 == 0 else axis_y + 45
        x0 = max(58, min(WIDTH - 58 - card_w, x - card_w / 2))
        parts.append(card(x0, y, card_w, card_h, node))
        parts.append(f'<line x1="{x:.1f}" y1="{axis_y + (12 if index % 2 == 0 else -12):.1f}" x2="{x:.1f}" y2="{y + (card_h if index % 2 == 0 else 0):.1f}" stroke="{PALETTE["line"]}" stroke-width="1.1"/>')
    if edges:
        relationship = compact(edges[0].get("label") or spec.relationships[0] if spec.relationships else "演进关系", 36)
        parts.append(text_block(relationship, 600, axis_y + 8, 360, size=12, fill=PALETTE["muted"], weight=500, anchor="middle", max_lines=1))
    return "\n".join(parts)


def render_flow(spec: FigureSpec, nodes: list[dict[str, str]], edges: list[dict[str, str]]) -> str:
    count = max(1, len(nodes))
    cols = min(4, count)
    rows = math.ceil(count / cols)
    left = 72
    top = 160 if rows <= 2 else 140
    gap_x = 42
    gap_y = 72 if rows <= 2 else 42
    card_w = (1056 - gap_x * (cols - 1)) / cols
    card_h = 82 if rows <= 2 else 70
    positions: dict[str, tuple[float, float, float, float]] = {}
    for index, node in enumerate(nodes):
        row = index // cols
        col = index % cols
        visual_col = cols - 1 - col if row % 2 == 1 else col
        x = left + visual_col * (card_w + gap_x)
        y = top + row * (card_h + gap_y)
        positions[node["id"]] = (x, y, card_w, card_h)
    flow_edges = [
        {"from": nodes[index]["id"], "to": nodes[index + 1]["id"], "label": "", "style": "solid", "direction": ""}
        for index in range(len(nodes) - 1)
    ]
    edge_lines, edge_labels = render_edge_set(flow_edges, positions, max_labels=0)
    node_parts = [card(*positions[node["id"]], node, index=index + 1) for index, node in enumerate(nodes)]
    return "\n".join(edge_lines + node_parts + edge_labels)


def render_sequence(spec: FigureSpec, nodes: list[dict[str, str]], edges: list[dict[str, str]]) -> str:
    participants = nodes[:6]
    count = max(1, len(participants))
    left = 95
    right = 1105
    gap = 0 if count == 1 else (right - left) / (count - 1)
    top = 148
    bottom = 628
    parts: list[str] = []
    xs: dict[str, float] = {}
    for index, node in enumerate(participants):
        x = left + index * gap
        xs[node["id"]] = x
        parts.append(card(x - 78, top, 156, 70, node))
        parts.append(f'<line x1="{x:.1f}" y1="{top + 82:.1f}" x2="{x:.1f}" y2="{bottom:.1f}" stroke="{PALETTE["line"]}" stroke-width="1.3" stroke-dasharray="6 6"/>')
    valid_edges = [edge for edge in edges if edge["from"] in xs and edge["to"] in xs]
    if not valid_edges:
        valid_edges = [
            {"from": participants[index]["id"], "to": participants[index + 1]["id"], "label": "", "style": "solid", "direction": ""}
            for index in range(len(participants) - 1)
        ]
    for index, edge in enumerate(valid_edges[:9]):
        y = top + 120 + index * 42
        x1 = xs[edge["from"]]
        x2 = xs[edge["to"]]
        offset = 18 if x2 >= x1 else -18
        line, label = edge_svg(x1 + offset, y, x2 - offset, y, edge["label"], dashed=edge.get("style") == "dashed", curve=False)
        parts.append(line)
        if label:
            parts.append(label)
    return "\n".join(parts)


def render_matrix(spec: FigureSpec, nodes: list[dict[str, str]], edges: list[dict[str, str]]) -> str:
    count = max(1, len(nodes))
    cols = min(3, count)
    rows = math.ceil(count / cols)
    left = 120
    top = 155
    gap_x = 38
    gap_y = 28
    cell_w = (960 - gap_x * (cols - 1)) / cols
    cell_h = min(112, max(78, (468 - gap_y * (rows - 1)) / rows))
    parts = [rect(left - 28, top - 34, 1016, 530, fill="#FFFFFF", stroke=PALETTE["line"], rx=12, sw=1.2, dash="8 4")]
    parts.append(text_block("关键维度对照", left, top - 10, 360, size=12, fill=PALETTE["muted"], weight=700, max_lines=1))
    for index, node in enumerate(nodes):
        row = index // cols
        col = index % cols
        x = left + col * (cell_w + gap_x)
        y = top + row * (cell_h + gap_y)
        parts.append(card(x, y, cell_w, cell_h, node, index=index + 1))
    return "\n".join(parts)


def render_topology(spec: FigureSpec, nodes: list[dict[str, str]], edges: list[dict[str, str]]) -> str:
    if len(nodes) <= 4:
        positions: dict[str, tuple[float, float, float, float]] = {}
        y_values = [158, 318, 500, 590]
        widths = [360, 430, 520, 430]
        parts: list[str] = []
        for index, node in enumerate(nodes):
            w = widths[min(index, len(widths) - 1)]
            h = 82
            x = (WIDTH - w) / 2
            y = y_values[min(index, len(y_values) - 1)]
            positions[node["id"]] = (x, y, w, h)
        topology_edges = [
            {"from": nodes[index]["id"], "to": nodes[index + 1]["id"], "label": "", "style": "solid", "direction": ""}
            for index in range(len(nodes) - 1)
        ] or edges[:1]
        edge_lines, edge_labels = render_edge_set(topology_edges, positions, max_labels=0)
        parts.extend(edge_lines)
        for index, node in enumerate(nodes):
            parts.append(card(*positions[node["id"]], node, index=index + 1))
        parts.extend(edge_labels)
        return "\n".join(parts)

    center_node = next((node for node in nodes if node.get("priority") == "primary"), nodes[0])
    others = [node for node in nodes if node["id"] != center_node["id"]]
    positions: dict[str, tuple[float, float, float, float]] = {center_node["id"]: (492, 330, 216, 86)}
    radius_x = 400
    radius_y = 205
    center_x = 600
    center_y = 373
    for index, node in enumerate(others):
        angle = -math.pi / 2 + index * 2 * math.pi / max(1, len(others))
        x = center_x + radius_x * math.cos(angle) - 92
        y = center_y + radius_y * math.sin(angle) - 36
        x = max(64, min(WIDTH - 64 - 184, x))
        y = max(140, min(HEIGHT - 126 - 72, y))
        positions[node["id"]] = (x, y, 184, 72)
    topology_edges = [
        {"from": center_node["id"], "to": node["id"], "label": "", "style": "solid", "direction": ""}
        for node in others
    ]
    edge_lines, edge_labels = render_edge_set(topology_edges, positions, max_labels=0)
    min_x = max(58, min(box[0] for box in positions.values()) - 28)
    min_y = max(132, min(box[1] for box in positions.values()) - 28)
    max_x = min(WIDTH - 58, max(box[0] + box[2] for box in positions.values()) + 28)
    max_y = min(660, max(box[1] + box[3] for box in positions.values()) + 28)
    parts = [rect(min_x, min_y, max_x - min_x, max_y - min_y, fill="#FFFFFF", stroke=PALETTE["line"], rx=12, sw=1.2, dash="8 4")]
    parts.extend(edge_lines)
    parts.append(card(*positions[center_node["id"]], center_node, index=1))
    for index, node in enumerate(others, start=2):
        parts.append(card(*positions[node["id"]], node, index=index))
    parts.extend(edge_labels)
    return "\n".join(parts)


def render_svg(spec: FigureSpec) -> str:
    nodes = normalize_nodes(spec)
    edges = normalize_edges(spec, nodes)
    if spec.figure_type == "timeline":
        body = render_timeline(spec, nodes, edges)
    elif spec.figure_type in {"layered", "pyramid"}:
        body = render_layered(spec, nodes, edges)
    elif spec.figure_type in {"flowchart", "dataflow", "lifecycle"}:
        body = render_flow(spec, nodes, edges)
    elif spec.figure_type == "sequence":
        body = render_sequence(spec, nodes, edges)
    elif spec.figure_type == "matrix":
        body = render_matrix(spec, nodes, edges)
    elif spec.figure_type == "topology":
        body = render_topology(spec, nodes, edges)
    else:
        body = render_architecture(spec, nodes, edges)
    return shell(spec, body, nodes)


def html_doc(spec: FigureSpec, svg: str) -> str:
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(spec.title)}</title>
  <style>
    html, body {{ margin: 0; padding: 0; background: #FFFFFF; }}
    body {{ min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
    svg {{ width: min(1200px, 100vw); height: auto; display: block; }}
  </style>
</head>
<body>
{svg}
</body>
</html>'''


def backup_existing(root: Path) -> str | None:
    if not root.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = Path(".data/backups") / f"polished-before-white-{stamp}"
    backup_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(root, backup_dir)
    return str(backup_dir)


def main() -> None:
    project = BookProject("config")
    state = project.load_write_checkpoint_with_workers("book-1")
    scan = scan_figure_specs(state, illustrations=state.style.illustrations)
    if scan.failed:
        raise SystemExit(json.dumps([failure.__dict__ for failure in scan.failed], ensure_ascii=False, indent=2))

    root = Path("assets/figures/polished")
    backup = backup_existing(root)
    root.mkdir(parents=True, exist_ok=True)

    generated = []
    for spec in scan.specs:
        chapter_dir = root / f"chapter-{spec.chapter_id:02d}"
        chapter_dir.mkdir(parents=True, exist_ok=True)
        stem = spec.figure_id
        svg = render_svg(spec)
        svg_path = chapter_dir / f"{stem}.svg"
        html_path = chapter_dir / f"{stem}.html"
        png_path = chapter_dir / f"{stem}.png"
        svg_path.write_text(svg, encoding="utf-8")
        html_path.write_text(html_doc(spec, svg), encoding="utf-8")
        render_svg_to_png(svg_path, png_path)
        generated.append(
            {
                "chapter": spec.chapter_id,
                "figure_id": spec.figure_id,
                "type": spec.figure_type,
                "svg": str(svg_path),
                "png": str(png_path),
            }
        )

    print(json.dumps({"generated": len(generated), "backup": backup, "assets_dir": str(root), "items": generated}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
