from __future__ import annotations

import html
import json
import math
import re
from pathlib import Path
from typing import Any

from core.figures import FigureSpec, render_svg_to_png, scan_figure_specs
from core.workflow import BookProject

WIDTH = 1200
HEIGHT = 760
FONT = "JetBrains Mono, SFMono-Regular, Menlo, Consolas, 'PingFang SC', 'Microsoft YaHei', monospace"

PALETTE = {
    "bg": "#020617",
    "panel": "#0f172a",
    "panel2": "#111827",
    "grid": "#1e293b",
    "border": "#334155",
    "text": "#e2e8f0",
    "muted": "#94a3b8",
    "line": "#64748b",
    "frontend": "#22d3ee",
    "backend": "#34d399",
    "database": "#a78bfa",
    "cloud": "#fbbf24",
    "security": "#fb7185",
    "bus": "#fb923c",
    "external": "#94a3b8",
}

TYPE_COLOR = {
    "application": "frontend",
    "frontend": "frontend",
    "edge": "frontend",
    "device": "frontend",
    "sensor": "frontend",
    "platform": "backend",
    "service": "backend",
    "backend": "backend",
    "data": "database",
    "database": "database",
    "storage": "database",
    "ai": "bus",
    "agent": "bus",
    "model": "bus",
    "security": "security",
    "auth": "security",
    "cloud": "cloud",
    "external": "external",
}


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def compact(value: object, limit: int = 28) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" ，。；;：:")
    text = text.replace("（最左蓝色节点）", "").replace("（左中蓝色节点）", "").replace("（右中蓝色节点）", "")
    text = text.replace("（最右橙色节点）", "").replace("（实线箭头）", "")
    if "：" in text:
        prefix, suffix = text.split("：", 1)
        text = prefix if len(prefix) <= 14 else suffix
    elif ":" in text:
        prefix, suffix = text.split(":", 1)
        text = prefix if len(prefix) <= 14 else suffix
    text = text.strip(" ，。；;：:")
    return text[:limit].rstrip() + ("…" if len(text) > limit else "")


def wrap(value: object, limit: int, max_lines: int) -> list[str]:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return []
    chunks: list[str] = []
    while text and len(chunks) < max_lines:
        chunks.append(text[:limit])
        text = text[limit:]
    if text and chunks:
        chunks[-1] = chunks[-1].rstrip(" ，。；;、") + "…"
    return chunks


def text_lines(
        value: object,
        x: float,
        y: float,
        width: float,
        *,
        size: int,
        fill: str,
        anchor: str = "start",
        max_lines: int = 2,
        weight: int = 500,
) -> str:
    char_width = size * 1.05
    limit = max(4, int(width / char_width))
    lines = wrap(value, limit, max_lines)
    parts = []
    for index, line in enumerate(lines):
        parts.append(
            f'<text x="{x:.1f}" y="{y + index * (size + 5):.1f}" fill="{fill}" font-size="{size}" '
            f'font-family="{FONT}" font-weight="{weight}" text-anchor="{anchor}">{esc(line)}</text>'
        )
    return "\n".join(parts)


def node_color(node: dict[str, str], index: int) -> str:
    raw = " ".join([node.get("type", ""), node.get("label", ""), node.get("subtitle", "")]).lower()
    for key, color_name in TYPE_COLOR.items():
        if key.lower() in raw:
            return PALETTE[color_name]
    return [PALETTE["backend"], PALETTE["frontend"], PALETTE["database"], PALETTE["bus"], PALETTE["cloud"], PALETTE["security"]][index % 6]


def normalize_nodes(spec: FigureSpec) -> list[dict[str, str]]:
    nodes: list[dict[str, str]] = []
    source = spec.components or []
    if not source:
        for index, item in enumerate((spec.elements or [spec.title])[:10], start=1):
            source.append({"id": f"n{index}", "label": item, "type": "external", "subtitle": ""})
    for index, item in enumerate(source[:10], start=1):
        label = compact(item.get("label") or item.get("id") or f"模块{index}", 22)
        subtitle = compact(item.get("subtitle") or item.get("role") or "", 34)
        nodes.append(
            {
                "id": str(item.get("id") or f"n{index}"),
                "label": label,
                "subtitle": subtitle,
                "type": str(item.get("type") or "external"),
                "group": str(item.get("group") or ""),
                "priority": str(item.get("priority") or "normal"),
                "shape": str(item.get("shape") or "card"),
            }
        )
    return nodes


def normalize_edges(spec: FigureSpec, nodes: list[dict[str, str]]) -> list[dict[str, str]]:
    node_ids = {node["id"] for node in nodes}
    edges: list[dict[str, str]] = []
    for item in spec.connections[:12]:
        source = str(item.get("from") or "")
        target = str(item.get("to") or "")
        if source in node_ids and target in node_ids and source != target:
            edges.append({"from": source, "to": target, "label": compact(item.get("label") or "主链路", 18), "style": str(item.get("style") or "solid")})
    if not edges:
        for index in range(max(0, len(nodes) - 1)):
            label = spec.relationships[index % len(spec.relationships)] if spec.relationships else "主链路"
            edges.append({"from": nodes[index]["id"], "to": nodes[index + 1]["id"], "label": compact(label, 18), "style": "solid"})
    return edges[:10]


def svg_shell(spec: FigureSpec, body: str, legend: str) -> str:
    subtitle = spec.audience_takeaway or spec.purpose or spec.visual_focus
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">
  <title id="title">{esc(spec.title)}</title>
  <desc id="desc">{esc(subtitle)}</desc>
  <defs>
    <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M 32 0 L 0 0 0 32" fill="none" stroke="{PALETTE['grid']}" stroke-width="0.65" opacity="0.58"/></pattern>
    <marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill="{PALETTE['line']}"/></marker>
    <filter id="glow" x="-30%" y="-30%" width="160%" height="170%"><feDropShadow dx="0" dy="10" stdDeviation="9" flood-color="#000000" flood-opacity="0.35"/></filter>
  </defs>
  <rect width="{WIDTH}" height="{HEIGHT}" fill="{PALETTE['bg']}"/>
  <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#grid)" opacity="0.8"/>
  <rect x="28" y="28" width="1144" height="704" rx="24" fill="rgba(15,23,42,0.72)" stroke="{PALETTE['border']}" stroke-width="1.4"/>
  <rect x="58" y="50" width="1084" height="78" rx="14" fill="rgba(15,23,42,0.95)" stroke="{PALETTE['border']}" stroke-width="1" filter="url(#glow)"/>
  <circle cx="82" cy="89" r="6" fill="{PALETTE['frontend']}"><animate attributeName="opacity" values="0.45;1;0.45" dur="2.4s" repeatCount="indefinite"/></circle>
  {text_lines(spec.title, 100, 82, 820, size=24, fill=PALETTE['text'], max_lines=1, weight=800)}
  {text_lines(subtitle, 100, 108, 930, size=11, fill=PALETTE['muted'], max_lines=1, weight=500)}
  {body}
  {legend}
</svg>'''


def card(x: float, y: float, w: float, h: float, node: dict[str, str], color: str, *, index: int | None = None) -> str:
    label = node["label"]
    subtitle = node.get("subtitle", "")
    badge = "" if index is None else f'<circle cx="{x + 20:.1f}" cy="{y + 22:.1f}" r="9" fill="{color}"/><text x="{x + 20:.1f}" y="{y + 26:.1f}" fill="{PALETTE["bg"]}" font-size="10" font-family="{FONT}" font-weight="800" text-anchor="middle">{index}</text>'
    label_x = x + (38 if index is not None else 18)
    return f'''
  <rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="10" fill="{PALETTE['panel']}"/>
  <rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="10" fill="{color}" opacity="0.16" stroke="{color}" stroke-width="1.6"/>
  <rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="5" rx="2.5" fill="{color}"/>
  {badge}
  {text_lines(label, label_x, y + 32, w - label_x + x - 14, size=13, fill=PALETTE['text'], max_lines=2, weight=700)}
  {text_lines(subtitle, label_x, y + h - 18, w - label_x + x - 14, size=9, fill=PALETTE['muted'], max_lines=1, weight=500)}'''


def arrow(x1: float, y1: float, x2: float, y2: float, label: str = "", dashed: bool = False) -> str:
    dash = ' stroke-dasharray="7 6"' if dashed else ""
    mid_x = (x1 + x2) / 2
    mid_y = (y1 + y2) / 2
    label_svg = "" if not label else text_lines(label, mid_x, mid_y - 6, 120, size=8, fill=PALETTE["muted"], anchor="middle", max_lines=1, weight=600)
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{PALETTE["line"]}" stroke-width="1.8" marker-end="url(#arrow)"{dash}/>{label_svg}'


def legend_svg(spec: FigureSpec) -> str:
    items = spec.legend[:4]
    if not items:
        return ""
    x, y, w, h = 70, 660, 1060, 48
    colors = [PALETTE["frontend"], PALETTE["backend"], PALETTE["database"], PALETTE["bus"]]
    parts = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="rgba(15,23,42,0.82)" stroke="{PALETTE["border"]}" stroke-width="1"/>']
    for index, item in enumerate(items):
        col = index % 2
        row = index // 2
        item_x = x + 24 + col * 510
        item_y = y + 20 + row * 20
        parts.append(f'<circle cx="{item_x}" cy="{item_y}" r="5" fill="{colors[index % len(colors)]}"/>')
        parts.append(text_lines(item, item_x + 14, item_y + 4, 450, size=8, fill=PALETTE["muted"], max_lines=1, weight=600))
    return "\n".join(parts)


def layout_grid(nodes: list[dict[str, str]]) -> dict[str, tuple[float, float, float, float]]:
    count = len(nodes)
    cols = 3 if count <= 9 else 4
    rows = math.ceil(count / cols)
    card_w = 250 if cols == 4 else 300
    card_h = 82 if rows <= 2 else 74
    gap_x = (1000 - cols * card_w) / max(1, cols - 1)
    gap_y = 42 if rows <= 2 else 28
    start_x = 100
    total_h = rows * card_h + (rows - 1) * gap_y
    start_y = 180 + max(0, (390 - total_h) / 2)
    return {node["id"]: (start_x + (i % cols) * (card_w + gap_x), start_y + (i // cols) * (card_h + gap_y), card_w, card_h) for i, node in enumerate(nodes)}


def render_network(spec: FigureSpec, nodes: list[dict[str, str]], edges: list[dict[str, str]], *, radial: bool = False) -> str:
    if radial and len(nodes) > 2:
        center = next((node for node in nodes if node.get("priority") == "primary"), nodes[0])
        positions = {center["id"]: (475, 340, 250, 92)}
        others = [node for node in nodes if node is not center]
        radius_x, radius_y = 420, 175
        for index, node in enumerate(others):
            angle = -math.pi / 2 + index * (2 * math.pi / max(1, len(others)))
            positions[node["id"]] = (600 + radius_x * math.cos(angle) - 115, 380 + radius_y * math.sin(angle) - 38, 230, 76)
    else:
        positions = layout_grid(nodes)
    parts: list[str] = []
    for edge_item in edges:
        if edge_item["from"] not in positions or edge_item["to"] not in positions:
            continue
        sx, sy, sw, sh = positions[edge_item["from"]]
        tx, ty, tw, th = positions[edge_item["to"]]
        parts.append(arrow(sx + sw, sy + sh / 2, tx, ty + th / 2, edge_item["label"], dashed=edge_item.get("style") in {"dashed", "async", "event"}))
    for index, node in enumerate(nodes, start=1):
        x, y, w, h = positions[node["id"]]
        parts.append(card(x, y, w, h, node, node_color(node, index)))
    return "\n".join(parts)


def render_timeline(spec: FigureSpec, nodes: list[dict[str, str]]) -> str:
    milestones = nodes[:7]
    start_x, end_x, y = 140, 1060, 390
    gap = (end_x - start_x) / max(1, len(milestones) - 1)
    parts = [arrow(start_x, y, end_x, y, "演进路径")]
    for index, node in enumerate(milestones):
        x = start_x + index * gap
        color = node_color(node, index)
        label_y = y - 76 if index % 2 == 0 else y + 62
        sub_y = label_y + 30
        parts.append(f'<circle cx="{x:.1f}" cy="{y}" r="16" fill="{color}" stroke="{PALETTE["panel"]}" stroke-width="4"/>')
        parts.append(text_lines(node["label"], x, label_y, 160, size=12, fill=PALETTE["text"], anchor="middle", max_lines=2, weight=800))
        parts.append(text_lines(node.get("subtitle", ""), x, sub_y, 170, size=8, fill=PALETTE["muted"], anchor="middle", max_lines=2, weight=500))
    return "\n".join(parts)


def render_layered(spec: FigureSpec, nodes: list[dict[str, str]]) -> str:
    labels = [node["label"] for node in nodes]
    is_compare = any("四层" in label for label in labels) and any("五层" in label for label in labels)
    parts: list[str] = []
    if is_compare:
        columns = [("传统四层", [n for n in nodes if "四层" in n["label"]]), ("增强五层", [n for n in nodes if "五层" in n["label"]])]
        for col, (title, col_nodes) in enumerate(columns):
            x = 150 + col * 470
            parts.append(f'<rect x="{x}" y="170" width="380" height="430" rx="14" fill="rgba(15,23,42,0.55)" stroke="{PALETTE["border"]}" stroke-dasharray="8 6"/>')
            parts.append(text_lines(title, x + 190, 200, 320, size=15, fill=PALETTE["text"], anchor="middle", max_lines=1, weight=800))
            layer_h = 52
            for index, node in enumerate(col_nodes[:6]):
                y = 240 + index * 62
                parts.append(card(x + 40, y, 300, layer_h, node, node_color(node, index)))
    else:
        layer_h = min(70, max(48, int(380 / max(1, len(nodes))) - 10))
        start_y = 175
        for index, node in enumerate(nodes[:7]):
            width = 810 if spec.figure_type == "layered" else 360 + index * 80
            x = 600 - width / 2
            y = start_y + index * (layer_h + 14)
            parts.append(card(x, y, width, layer_h, node, node_color(node, index)))
            if index < len(nodes[:7]) - 1:
                parts.append(arrow(600, y + layer_h + 2, 600, y + layer_h + 13, ""))
    return "\n".join(parts)


def render_flow(spec: FigureSpec, nodes: list[dict[str, str]], edges: list[dict[str, str]]) -> str:
    count = len(nodes)
    card_w = 220 if count <= 5 else 190
    card_h = 76
    per_row = min(4, count)
    gap_x = (980 - per_row * card_w) / max(1, per_row - 1)
    positions: dict[str, tuple[float, float, float, float]] = {}
    for index, node in enumerate(nodes):
        row = index // per_row
        col = index % per_row
        if row % 2 == 1:
            col = per_row - 1 - col
        positions[node["id"]] = (110 + col * (card_w + gap_x), 220 + row * 130, card_w, card_h)
    parts = []
    for index in range(len(nodes) - 1):
        source = positions[nodes[index]["id"]]
        target = positions[nodes[index + 1]["id"]]
        label = edges[index]["label"] if index < len(edges) else ""
        parts.append(arrow(source[0] + source[2], source[1] + source[3] / 2, target[0], target[1] + target[3] / 2, label))
    for index, node in enumerate(nodes, start=1):
        x, y, w, h = positions[node["id"]]
        parts.append(card(x, y, w, h, node, node_color(node, index), index=index))
    return "\n".join(parts)


def render_sequence(spec: FigureSpec, nodes: list[dict[str, str]], edges: list[dict[str, str]]) -> str:
    participants = nodes[:6]
    start_x, gap = 130, 188
    top, bottom = 190, 600
    parts = []
    xs = []
    for index, node in enumerate(participants):
        x = start_x + index * gap
        xs.append(x)
        parts.append(card(x - 70, top, 140, 58, node, node_color(node, index)))
        parts.append(f'<line x1="{x}" y1="{top + 64}" x2="{x}" y2="{bottom}" stroke="{PALETTE["border"]}" stroke-width="1" stroke-dasharray="6 6"/>')
    for index, edge_item in enumerate(edges[:8]):
        source_idx = next((i for i, n in enumerate(participants) if n["id"] == edge_item["from"]), index % max(1, len(participants) - 1))
        target_idx = next((i for i, n in enumerate(participants) if n["id"] == edge_item["to"]), min(source_idx + 1, len(participants) - 1))
        if source_idx == target_idx:
            target_idx = min(source_idx + 1, len(participants) - 1)
        y = 285 + index * 38
        parts.append(arrow(xs[source_idx] + 18, y, xs[target_idx] - 18, y, edge_item["label"], dashed=index % 2 == 1))
    return "\n".join(parts)


def render_matrix(spec: FigureSpec, nodes: list[dict[str, str]]) -> str:
    parts = []
    cols = 3
    cell_w, cell_h = 290, 88
    start_x, start_y = 170, 200
    for index, node in enumerate(nodes[:9]):
        x = start_x + (index % cols) * (cell_w + 45)
        y = start_y + (index // cols) * (cell_h + 34)
        parts.append(card(x, y, cell_w, cell_h, node, node_color(node, index)))
    return "\n".join(parts)


def render_svg(spec: FigureSpec) -> str:
    nodes = normalize_nodes(spec)
    edges = normalize_edges(spec, nodes)
    if spec.figure_type == "timeline":
        body = render_timeline(spec, nodes)
    elif spec.figure_type in {"layered", "pyramid"}:
        body = render_layered(spec, nodes)
    elif spec.figure_type in {"flowchart", "lifecycle", "dataflow"}:
        body = render_flow(spec, nodes, edges)
    elif spec.figure_type == "sequence":
        body = render_sequence(spec, nodes, edges)
    elif spec.figure_type == "matrix":
        body = render_matrix(spec, nodes)
    elif spec.figure_type == "topology":
        body = render_network(spec, nodes, edges, radial=True)
    else:
        body = render_network(spec, nodes, edges)
    return svg_shell(spec, body, legend_svg(spec))


def html_doc(spec: FigureSpec, svg: str) -> str:
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(spec.title)}</title>
  <style>
    body {{ margin: 0; background: {PALETTE['bg']}; display: grid; place-items: center; min-height: 100vh; }}
    svg {{ width: min(1200px, 100vw); height: auto; display: block; }}
  </style>
</head>
<body>
{svg}
</body>
</html>'''


def main() -> None:
    project = BookProject("config")
    state = project.load_write_checkpoint_with_workers("book-1")
    scan = scan_figure_specs(state, illustrations=state.style.illustrations)
    if scan.failed:
        raise SystemExit(json.dumps([failure.__dict__ for failure in scan.failed], ensure_ascii=False, indent=2))
    root = Path("assets/figures/polished")
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
        generated.append({"chapter": spec.chapter_id, "figure_id": spec.figure_id, "type": spec.figure_type, "png": str(png_path)})
    print(json.dumps({"generated": len(generated), "assets_dir": str(root), "items": generated}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
