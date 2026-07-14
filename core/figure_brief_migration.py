"""一次性升级旧版 `book-figure` 为出版级结构化 brief。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

from core.markdown_assets import iter_book_figure_blocks, normalize_book_figure_scalar, parse_book_figure_payload

_ALLOWED_TYPES = {
    "architecture",
    "sequence",
    "flowchart",
    "dataflow",
    "pyramid",
    "layered",
    "topology",
    "lifecycle",
    "matrix",
    "timeline",
}
_TYPE_ALIASES = {
    "sequence_diagram": "sequence",
    "sequence diagram": "sequence",
    "flow_chart": "flowchart",
    "data_flow": "dataflow",
    "layered_architecture": "layered",
    "layered-architecture": "layered",
    "layered_stack_3column": "matrix",
    "architecture_diagram": "architecture",
    "table": "matrix",
}
_GENERIC_LABEL_RE = re.compile(r"^(?:节点|决策节点|判断节点|处理节点|计算节点|执行节点|开始节点|结束状态|输入数据源|输出节点|最左侧|最右侧|左侧|右侧)\d*$")
_BOOK_FIGURE_RE_TEMPLATE = r"```{marker}\s*\n(?P<body>.*?)\n```"
_OUTPUT_FIELDS = [
    "id",
    "type",
    "title",
    "purpose",
    "audience_takeaway",
    "visual_focus",
    "design_level",
    "layout",
    "elements",
    "relationships",
    "regions",
    "components",
    "connections",
    "callouts",
    "legend",
    "caption",
    "visual_constraints",
    "render_notes",
]


@dataclass(frozen=True)
class FigureBriefUpgradeResult:
    """Markdown 图表 brief 升级结果。"""

    markdown: str
    total_blocks: int
    changed_blocks: int
    repaired_blocks: int
    failed_blocks: int
    failures: list[str]


@dataclass(frozen=True)
class FigureBriefSyncResult:
    """章节合稿图表 brief 与小节 brief 同步结果。"""

    markdown: str
    total_blocks: int
    changed_blocks: int
    unmatched_blocks: int
    inserted_blocks: int = 0


@dataclass(frozen=True)
class _FigureBriefEntry:
    index: int
    section_id: str
    body: str
    payload: dict[str, Any]
    id_key: str
    number_key: str
    title_key: str


def upgrade_book_figure_briefs(markdown: str, *, marker: str = "book-figure") -> FigureBriefUpgradeResult:
    """把 Markdown 中的旧版 `book-figure` 块升级为新版出版级结构化 brief。"""
    blocks = iter_book_figure_blocks(markdown, marker)
    if not blocks:
        return FigureBriefUpgradeResult(markdown, 0, 0, 0, 0, [])

    parts: list[str] = []
    cursor = 0
    changed = 0
    repaired = 0
    failures: list[str] = []
    for index, block in enumerate(blocks, start=1):
        parts.append(markdown[cursor:block.start])
        payload, repair_reason = _load_legacy_payload(block.body)
        if payload is None:
            failures.append(f"第{index}个 `{marker}` 无法迁移: {repair_reason}")
            parts.append(markdown[block.start:block.end])
            cursor = block.end
            continue
        upgraded = _upgrade_payload(payload, occurrence=index)
        new_block = f"```{marker}\n{_dump_yaml(upgraded)}```"
        old_block = markdown[block.start:block.end]
        if new_block != old_block:
            changed += 1
        if repair_reason:
            repaired += 1
        parts.append(new_block)
        cursor = block.end
    parts.append(markdown[cursor:])
    return FigureBriefUpgradeResult(
        markdown="".join(parts),
        total_blocks=len(blocks),
        changed_blocks=changed,
        repaired_blocks=repaired,
        failed_blocks=len(failures),
        failures=failures,
    )


def sync_chapter_figure_briefs_from_sections(
        chapter_markdown: str,
        section_markdowns: list[str],
        *,
        marker: str = "book-figure",
        min_chapter_figures: int = 1,
) -> FigureBriefSyncResult:
    """用小节中的高质量图表 brief 同步章节合稿中的同名/同号图表。"""
    chapter_blocks = iter_book_figure_blocks(chapter_markdown, marker)
    section_entries = _section_figure_entries(section_markdowns, marker=marker)
    if not chapter_blocks and not section_entries:
        return FigureBriefSyncResult(chapter_markdown, 0, 0, 0)
    if not chapter_blocks:
        selected_entries = _select_additional_figures(section_entries, used_entries=set(), count=max(0, min_chapter_figures))
        markdown = _insert_figure_entries(chapter_markdown, selected_entries, marker=marker)
        inserted = len(selected_entries)
        return FigureBriefSyncResult(markdown, inserted, inserted, 0, inserted)

    if not section_entries:
        return FigureBriefSyncResult(chapter_markdown, len(chapter_blocks), 0, len(chapter_blocks))
    indexes = _figure_entry_indexes(section_entries)
    used_entries: set[int] = set()

    parts: list[str] = []
    cursor = 0
    changed = 0
    unmatched = 0
    for block in chapter_blocks:
        parts.append(chapter_markdown[cursor:block.start])
        chapter_payload, _reason = parse_book_figure_payload(block.body)
        match = _match_section_figure(chapter_payload or {}, indexes, used_entries)
        if match is None:
            unmatched += 1
            parts.append(chapter_markdown[block.start:block.end])
        else:
            used_entries.add(match.index)
            merged_payload = _merge_synced_figure_payload(match.payload, chapter_payload or {})
            new_block = f"```{marker}\n{_dump_yaml(merged_payload)}```"
            if new_block != chapter_markdown[block.start:block.end]:
                changed += 1
            parts.append(new_block)
        cursor = block.end
    parts.append(chapter_markdown[cursor:])
    markdown = "".join(parts)
    inserted = 0
    if len(chapter_blocks) < min_chapter_figures:
        selected_entries = _select_additional_figures(section_entries, used_entries=used_entries, count=min_chapter_figures - len(chapter_blocks))
        markdown = _insert_figure_entries(markdown, selected_entries, marker=marker)
        inserted = len(selected_entries)
    return FigureBriefSyncResult(markdown, len(chapter_blocks) + inserted, changed + inserted, unmatched, inserted)


def _section_figure_entries(section_markdowns: list[str], *, marker: str) -> list[_FigureBriefEntry]:
    entries: list[_FigureBriefEntry] = []
    for markdown in section_markdowns:
        section_id = _section_id_from_markdown(markdown)
        for block in iter_book_figure_blocks(markdown, marker):
            payload, _reason = parse_book_figure_payload(block.body)
            if payload is None:
                continue
            entries.append(
                _FigureBriefEntry(
                    index=len(entries),
                    section_id=section_id,
                    body=block.body,
                    payload=payload,
                    id_key=_figure_id_key(payload),
                    number_key=_figure_number_key(payload),
                    title_key=_figure_title_key(payload),
                )
            )
    return entries


def _select_additional_figures(entries: list[_FigureBriefEntry], *, used_entries: set[int], count: int) -> list[_FigureBriefEntry]:
    if count <= 0:
        return []
    candidates = [entry for entry in entries if entry.index not in used_entries]
    candidates.sort(key=lambda entry: (_figure_selection_score(entry.payload), entry.index))
    return candidates[:count]


def _figure_selection_score(payload: dict[str, Any]) -> int:
    figure_type = _scalar(payload.get("type")).lower()
    return {
        "architecture": 0,
        "layered": 1,
        "matrix": 2,
        "dataflow": 3,
        "flowchart": 4,
        "sequence": 5,
        "topology": 6,
        "timeline": 7,
        "lifecycle": 8,
        "pyramid": 9,
    }.get(figure_type, 10)


def _insert_figure_entries(markdown: str, entries: list[_FigureBriefEntry], *, marker: str) -> str:
    if not entries:
        return markdown
    insertions = [(_figure_insert_position(markdown, entry.section_id), f"\n\n```{marker}\n{entry.body}\n```") for entry in entries]
    result = markdown
    for position, block in sorted(insertions, key=lambda item: item[0], reverse=True):
        result = result[:position] + block + result[position:]
    return result


def _figure_insert_position(markdown: str, section_id: str) -> int:
    if section_id:
        match = re.search(rf"(?m)^###\s+{re.escape(section_id)}(?:\s|$).*?$", markdown)
        if match:
            return match.end()
    fallback = re.search(r"(?m)^###\s+.+$", markdown) or re.search(r"(?m)^##\s+.+$", markdown) or re.search(r"(?m)^#\s+.+$", markdown)
    return fallback.end() if fallback else 0


def _section_id_from_markdown(markdown: str) -> str:
    match = re.search(r"(?m)^###\s+(\d+(?:\.\d+){2})(?:\s|$)", markdown)
    return match.group(1) if match else ""


def _figure_entry_indexes(entries: list[_FigureBriefEntry]) -> dict[str, dict[str, list[_FigureBriefEntry]]]:
    indexes: dict[str, dict[str, list[_FigureBriefEntry]]] = {"id": {}, "number": {}, "title": {}}
    for entry in entries:
        for index_name, key in [("id", entry.id_key), ("number", entry.number_key), ("title", entry.title_key)]:
            if not key:
                continue
            indexes[index_name].setdefault(key, []).append(entry)
    return indexes


def _match_section_figure(
        chapter_payload: dict[str, Any],
        indexes: dict[str, dict[str, list[_FigureBriefEntry]]],
        used_entries: set[int],
) -> _FigureBriefEntry | None:
    keys = {
        "id": _figure_id_key(chapter_payload),
        "number": _figure_number_key(chapter_payload),
        "title": _figure_title_key(chapter_payload),
    }
    for index_name in ["title", "id", "number"]:
        key = keys[index_name]
        if not key:
            continue
        candidates = [entry for entry in indexes[index_name].get(key, []) if entry.index not in used_entries]
        if index_name != "title" and keys["title"]:
            candidates = [entry for entry in candidates if _figure_titles_compatible(keys["title"], entry.title_key)]
        if len(candidates) == 1:
            return candidates[0]
    return None


def _figure_titles_compatible(chapter_title_key: str, section_title_key: str) -> bool:
    if not chapter_title_key or not section_title_key:
        return True
    return chapter_title_key == section_title_key or chapter_title_key in section_title_key or section_title_key in chapter_title_key


def _merge_synced_figure_payload(section_payload: dict[str, Any], chapter_payload: dict[str, Any]) -> dict[str, Any]:
    merged = dict(section_payload)
    chapter_id = _scalar(chapter_payload.get("id"))
    if chapter_id:
        merged["id"] = chapter_id
    chapter_title = _scalar(chapter_payload.get("title"))
    section_title = _scalar(section_payload.get("title"))
    if _figure_number_from_text(chapter_title) and not _figure_number_from_text(section_title):
        merged["title"] = chapter_title
    return {field: merged[field] for field in _OUTPUT_FIELDS if field in merged}


def _figure_id_key(payload: dict[str, Any]) -> str:
    value = _scalar(payload.get("id"))
    return _canonical_text(value)


def _figure_number_key(payload: dict[str, Any]) -> str:
    for field in ["id", "title", "caption"]:
        key = _figure_number_from_text(_scalar(payload.get(field)))
        if key:
            return key
    return ""


def _figure_title_key(payload: dict[str, Any]) -> str:
    for field in ["title", "caption"]:
        value = _scalar(payload.get(field))
        if value:
            return _canonical_title(value)
    return ""


def _figure_number_from_text(value: str) -> str:
    text = value.lower().replace("—", "-").replace("_", "-")
    match = re.search(r"(?:fig(?:ure)?|tbl|图|表)?\s*-?\s*(\d+(?:\s*[-.]\s*\d+)+)", text)
    if not match:
        return ""
    parts = [str(int(part)) for part in re.split(r"\s*[-.]\s*", match.group(1)) if part.isdigit()]
    return "-".join(parts)


def _canonical_title(value: str) -> str:
    text = re.sub(r"^(?:图|表)?\s*\d+(?:\s*[-—_.]\s*\d+)*\s*", "", value).strip()
    text = re.sub(r"^假设场景\s*[-—：:]*\s*", "", text)
    text = re.sub(r"[（(]假设场景[）)]", "", text)
    return _canonical_text(text)


def _canonical_text(value: str) -> str:
    text = normalize_book_figure_scalar(value).lower()
    text = re.sub(r"[\s\-_—:：，,。.;；、（）()]+", "", text)
    return text


def _load_legacy_payload(body: str) -> tuple[dict[str, Any] | None, str]:
    candidates = [(body, "")]
    repaired = _repair_common_yaml(body)
    if repaired != body:
        candidates.append((repaired, "已修复常见 YAML/JSON 片段"))
    stripped = _strip_leading_slug_line(repaired)
    if stripped != repaired:
        candidates.append((stripped, "已移除规格块开头的孤立 id 行"))
    for candidate, reason in candidates:
        try:
            raw = yaml.safe_load(candidate)
        except yaml.YAMLError:
            continue
        if isinstance(raw, dict):
            return _unwrap_payload(raw), reason
    fallback = _fallback_payload_from_text(body)
    if fallback:
        return fallback, "已用文本兜底提取核心字段"
    return None, "YAML/JSON 无法解析，文本兜底也未提取到 title/caption"


def _unwrap_payload(raw: dict[str, Any]) -> dict[str, Any]:
    normalized = {_key(key): value for key, value in raw.items() if _key(key)}
    nested = normalized.get("figure")
    if isinstance(nested, dict):
        return {_key(key): value for key, value in nested.items() if _key(key)}
    nested = normalized.get("book-figure") or normalized.get("book_figure")
    if isinstance(nested, dict):
        return {_key(key): value for key, value in nested.items() if _key(key)}
    return normalized


def _repair_common_yaml(body: str) -> str:
    text = body.strip()
    text = re.sub(r"(?m)^(\s*[A-Za-z_][\w-]*:\s*\"[^\n\"]*)[”]$", r'\1"', text)
    text = re.sub(r"(?m)^(\s*[A-Za-z_][\w-]*:\s*[^\n]+),$", r"\1", text)
    return _repair_shorthand_relationship_lines(text)


def _strip_leading_slug_line(body: str) -> str:
    lines = body.splitlines()
    if len(lines) < 2:
        return body
    first = lines[0].strip()
    if first and ":" not in first and first not in {"{", "["} and not first.startswith("-"):
        return "\n".join(lines[1:]).strip()
    return body


def _repair_shorthand_relationship_lines(body: str) -> str:
    repaired: list[str] = []
    pattern = re.compile(r"^(?P<indent>\s*)-\s*from:\s*(?P<source>.+?)\s+to\s+(?P<target>[^\s(]+)(?:\s*\(label:\s*[\"“]?(?P<label>.+?)[\"”]?\))?\s*$")
    for line in body.splitlines():
        match = pattern.match(line)
        if match:
            indent = match.group("indent")
            source = _quote_yaml(match.group("source"))
            target = _quote_yaml(match.group("target"))
            label = _quote_yaml(match.group("label") or "")
            repaired.extend([f"{indent}- from: {source}", f"{indent}  to: {target}"])
            if label != '""':
                repaired.append(f"{indent}  label: {label}")
            continue
        repaired.append(line)
    return "\n".join(repaired)


def _fallback_payload_from_text(body: str) -> dict[str, Any] | None:
    title = _regex_field(body, "title")
    caption = _regex_field(body, "caption")
    if not title and not caption:
        return None
    return {
        "id": _regex_field(body, "id") or _figure_id_from_title(title or caption, 1),
        "type": _regex_field(body, "type") or _regex_field(body, "layout") or "architecture",
        "title": title or caption,
        "purpose": _regex_field(body, "purpose") or caption or title,
        "layout": _regex_field(body, "layout") or "按图表语义自动布局",
        "elements": _regex_list_block(body, "elements") or [title or caption],
        "relationships": _regex_list_block(body, "relationships") or [_regex_field(body, "purpose") or caption or title],
        "legend": _regex_list_block(body, "legend") or ["蓝色=核心能力；橙色=智能/风险路径。"],
        "caption": caption or title,
        "render_notes": _regex_field(body, "render_notes") or "HTML/SVG 统一绘制，使用出版级图表样式。",
    }


def _upgrade_payload(raw: dict[str, Any], *, occurrence: int) -> dict[str, Any]:
    existing = _existing_professional_payload(raw)
    if existing is not None:
        return existing
    figure_type = _figure_type(raw)
    title = _scalar(raw.get("title")) or _scalar(raw.get("name")) or f"图表 {occurrence}"
    caption = _scalar(raw.get("caption")) or title
    figure_id = _scalar(raw.get("id")) or _figure_id_from_title(title or caption, occurrence)
    purpose = _scalar(raw.get("purpose")) or caption
    layout = _layout_text(raw, figure_type)
    elements = _elements(raw, title=title)
    relationships = _relationships(raw)
    legend = _legend(raw)
    render_notes = _render_notes(raw)
    components = _components(raw, elements, figure_type=figure_type)
    connections = _connections(raw, relationships, components)
    regions = _regions(raw, components)
    return {
        "id": figure_id,
        "type": figure_type,
        "title": title,
        "purpose": purpose,
        "audience_takeaway": _scalar(raw.get("audience_takeaway")) or _audience_takeaway(title, purpose),
        "visual_focus": _scalar(raw.get("visual_focus")) or _visual_focus(components, connections, purpose),
        "design_level": _scalar(raw.get("design_level")) or _design_level(figure_type),
        "layout": layout,
        "elements": elements,
        "relationships": relationships or [purpose],
        "regions": regions,
        "components": components,
        "connections": connections,
        "callouts": _callouts(raw, relationships, purpose),
        "legend": legend,
        "caption": caption,
        "visual_constraints": _visual_constraints(raw, figure_type),
        "render_notes": render_notes,
    }


def _existing_professional_payload(raw: dict[str, Any]) -> dict[str, Any] | None:
    if not all(field in raw for field in _OUTPUT_FIELDS):
        return None
    if not isinstance(raw.get("components"), list) or not isinstance(raw.get("connections"), list):
        return None
    payload = {field: raw[field] for field in _OUTPUT_FIELDS}
    payload["type"] = _figure_type(raw)
    return payload


def _figure_type(raw: dict[str, Any]) -> str:
    value = _scalar(raw.get("type")).lower() or _scalar(raw.get("layout")).lower()
    value = value.replace(" ", "_")
    value = _TYPE_ALIASES.get(value, value)
    if value in _ALLOWED_TYPES:
        return value
    layout = raw.get("layout")
    if isinstance(layout, dict) and _list_items(layout.get("participants")):
        return "sequence"
    if _list_items(raw.get("layers")):
        return "layered"
    if _list_items(raw.get("nodes")):
        return "flowchart"
    return "architecture"


def _layout_text(raw: dict[str, Any], figure_type: str) -> str:
    layout = raw.get("layout")
    if isinstance(layout, str) and layout.strip():
        return normalize_book_figure_scalar(layout)
    if isinstance(layout, dict):
        orientation = _scalar(layout.get("orientation"))
        participants = [_scalar(item.get("name")) for item in _dict_items(layout.get("participants"))]
        if participants:
            return f"{orientation or 'horizontal'} 时序布局，参与者：{'、'.join(participants[:8])}。"
    return {
        "sequence": "从左到右时序布局，顶部为参与者，消息按时间向下排列。",
        "flowchart": "从左到右流程布局，决策节点使用菱形，关键路径用强调色。",
        "layered": "自下而上分层布局，强调层次职责和上下游关系。",
        "matrix": "矩阵布局，按比较维度分组呈现。",
        "timeline": "时间线布局，按阶段从左到右展开。",
    }.get(figure_type, "架构布局，强调边界、组件职责和主链路。")


def _elements(raw: dict[str, Any], *, title: str) -> list[str]:
    layers = _dict_items(raw.get("layers"))
    if layers:
        return [f"{_scalar(layer.get('layer')) or _scalar(layer.get('label'))}: {_scalar(layer.get('description'))}" for layer in layers]
    layout = raw.get("layout")
    if isinstance(layout, dict):
        participants = _dict_items(layout.get("participants"))
        if participants:
            return [f"{_scalar(item.get('name'))}: {_scalar(item.get('role'))}" for item in participants]
    value = raw.get("elements") or raw.get("nodes") or raw.get("components")
    nested_layers = _nested_layer_items(value)
    if nested_layers:
        return [f"{side}-{layer}" for side, layer in nested_layers]
    items = _string_items(value)
    return items or [title]


def _relationships(raw: dict[str, Any]) -> list[str]:
    items = _string_items(raw.get("relationships"))
    if items:
        return _split_relationship_sentences(items)
    message_items = _dict_items(raw.get("elements"))
    messages = [_relationship_from_dict(item) for item in message_items if item.get("from") or item.get("to")]
    return [item for item in messages if item]


def _legend(raw: dict[str, Any]) -> list[str]:
    items = _string_items(raw.get("legend"))
    if items:
        return items[:6]
    return ["蓝色=核心平台/主链路；青绿色=设备与边缘；橙色=AI/风险/关键决策。"]


def _render_notes(raw: dict[str, Any]) -> str:
    notes = _scalar(raw.get("render_notes"))
    return notes or "HTML/SVG 统一绘制，浅色背景，圆角矩形，短标签节点，底部图例和出版级图注。"


def _components(raw: dict[str, Any], elements: list[str], *, figure_type: str) -> list[dict[str, str]]:
    explicit = _component_items(raw.get("components"))
    if explicit and not _components_look_too_generic(explicit):
        return explicit[:10]
    protocol_components = _protocol_matrix_components(raw)
    if protocol_components:
        return protocol_components[:10]
    layout = raw.get("layout")
    if isinstance(layout, dict):
        participants = _dict_items(layout.get("participants"))
        if participants:
            return [_component_from_participant(item, index) for index, item in enumerate(participants[:8], start=1)]
    layers = _dict_items(raw.get("layers"))
    if layers:
        return [_component_from_layer(item, index) for index, item in enumerate(layers[:8], start=1)]
    nested_layers = _nested_layer_items(raw.get("elements"))
    if nested_layers:
        return [_component_from_endpoint(f"{side}-{layer}", index) for index, (side, layer) in enumerate(nested_layers[:10], start=1)]
    nodes = _dict_items(raw.get("nodes"))
    if nodes:
        return [_component_from_node(item, index) for index, item in enumerate(nodes[:10], start=1)]
    relation_endpoint_components = _components_from_structured_relationships(raw.get("relationships"))
    if relation_endpoint_components:
        return relation_endpoint_components[:10]
    element_dicts = _dict_items(raw.get("elements"))
    if element_dicts:
        return [_component_from_node(item, index) for index, item in enumerate(element_dicts[:10], start=1)]
    relation_components = _components_from_relationship_endpoints(_string_items(raw.get("relationships")))
    if relation_components:
        return relation_components[:10]
    if explicit:
        return explicit[:10]
    return [_component_from_text(item, index, figure_type=figure_type) for index, item in enumerate(elements[:10], start=1)]


def _connections(raw: dict[str, Any], relationships: list[str], components: list[dict[str, str]]) -> list[dict[str, str]]:
    explicit = _connection_items(raw.get("connections"), components)
    if explicit:
        return explicit[:12]
    relation_dicts = _connection_items(raw.get("relationships"), components)
    if relation_dicts:
        return relation_dicts[:12]
    relation_strings = _connections_from_relationship_strings(relationships, components)
    if relation_strings:
        return relation_strings[:12]
    message_dicts = _connection_items(raw.get("elements"), components)
    if message_dicts:
        return message_dicts[:12]
    protocol_connections = _protocol_matrix_connections(components)
    if protocol_connections:
        return protocol_connections[:12]
    if len(components) < 2:
        return []
    labels = relationships or ["主链路"] * (len(components) - 1)
    connections = []
    for index in range(min(len(components) - 1, 10)):
        label = _edge_label(labels[index % len(labels)]) or "主链路"
        connections.append(
            {
                "from": components[index]["id"],
                "to": components[index + 1]["id"],
                "label": label,
                "style": _edge_style(label),
                "direction": "left-to-right",
            }
        )
    return connections


def _regions(raw: dict[str, Any], components: list[dict[str, str]]) -> list[dict[str, str]]:
    explicit = _region_items(raw.get("regions") or raw.get("lanes"))
    if explicit:
        return explicit[:4]
    protocol_regions = _protocol_regions(components)
    if protocol_regions:
        return protocol_regions
    seen: list[str] = []
    for component in components:
        group = component.get("group", "")
        if group and group not in seen:
            seen.append(group)
    return [{"id": group, "label": _region_label(group), "role": _region_role(group)} for group in seen[:4]]


def _callouts(raw: dict[str, Any], relationships: list[str], purpose: str) -> list[str]:
    items = _string_items(raw.get("callouts"))
    if items:
        return items[:3]
    source = relationships or [purpose]
    return [_short(_clean_generic_references(item), 58) for item in source[:3] if item]


def _visual_constraints(raw: dict[str, Any], figure_type: str) -> list[str]:
    items = _string_items(raw.get("visual_constraints"))
    if items:
        return items[:4]
    base = ["节点标签使用短名词短语，解释性文字放入 callouts 或正文。", "图例放在底部，不遮挡主体结构。"]
    if figure_type in {"architecture", "topology", "dataflow"}:
        base.append("优先表达边界和主链路，不把所有概念塞进一张图。")
    if figure_type in {"flowchart", "lifecycle"}:
        base.append("决策节点必须写成可判断的问题或动作，分支标签保持短句。")
    return base


def _protocol_matrix_components(raw: dict[str, Any]) -> list[dict[str, str]]:
    columns = _protocol_columns_from_layout_text(_scalar(raw.get("layout")))
    if len(columns) < 2:
        return []
    row_specs = [
        ("scenario", "典型场景", "application", "application_domain", "card"),
        ("model", "通信模型", "platform", "platform_domain", "bus"),
        ("transport", "传输层", "edge", "edge_domain", "bus"),
    ]
    components: list[dict[str, str]] = []
    for field, row_label, component_type, _default_group, shape in row_specs:
        for protocol in _ordered_protocols(columns):
            value = columns[protocol].get(field, "")
            if not value:
                continue
            protocol_id = protocol.lower()
            components.append(
                {
                    "id": f"{protocol_id}_{field}",
                    "label": _short(value, 20),
                    "type": component_type,
                    "subtitle": f"{protocol} · {row_label}",
                    "group": f"protocol_{protocol_id}",
                    "priority": "primary" if protocol == "MQTT" and field == "model" else "normal",
                    "shape": shape,
                }
            )
    return components


def _protocol_columns_from_layout_text(value: str) -> dict[str, dict[str, str]]:
    if not value or not all(protocol in value for protocol in ["HTTP", "MQTT", "CoAP"]):
        return {}
    pattern = re.compile(r"(?:^|\s+-\s*)(?:左列|中列|右列)[（(](HTTP|MQTT|CoAP)[）)][:：](.*?)(?=\s+-\s*(?:左列|中列|右列)[（(]|$)")
    columns: dict[str, dict[str, str]] = {}
    for match in pattern.finditer(value):
        protocol = match.group(1)
        body = match.group(2)
        columns[protocol] = {
            "scenario": _protocol_layer_value(body, "顶层", "中层"),
            "model": _protocol_layer_value(body, "中层", "底层"),
            "transport": _protocol_layer_value(body, "底层", ""),
        }
    return {protocol: values for protocol, values in columns.items() if any(values.values())}


def _protocol_layer_value(body: str, label: str, next_label: str) -> str:
    next_pattern = rf"(?=\s+-\s*{re.escape(next_label)})" if next_label else r"$"
    match = re.search(rf"{re.escape(label)}.*?{next_pattern}", body)
    if not match:
        return ""
    quoted = _quoted_fragments(match.group(0))
    return " / ".join(quoted[:3])


def _quoted_fragments(value: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"[‘'\"“]([^’'\"”]{1,80})(?:[’'\"”]|$)", value) if match.group(1).strip()]


def _ordered_protocols(columns: dict[str, dict[str, str]]) -> list[str]:
    ordered = [protocol for protocol in ["HTTP", "MQTT", "CoAP"] if protocol in columns]
    ordered.extend(protocol for protocol in columns if protocol not in ordered)
    return ordered


def _protocol_matrix_connections(components: list[dict[str, str]]) -> list[dict[str, str]]:
    component_ids = {component["id"] for component in components}
    if not {"http_model", "mqtt_model", "coap_model"}.issubset(component_ids):
        return []
    connections: list[dict[str, str]] = []
    for protocol in ["http", "mqtt", "coap"]:
        transport = f"{protocol}_transport"
        model = f"{protocol}_model"
        scenario = f"{protocol}_scenario"
        if transport in component_ids and model in component_ids:
            connections.append({"from": transport, "to": model, "label": "承载", "style": "solid", "direction": "bottom-to-top"})
        if model in component_ids and scenario in component_ids:
            connections.append({"from": model, "to": scenario, "label": "适用", "style": "solid", "direction": "bottom-to-top"})
    connections.append({"from": "mqtt_model", "to": "http_model", "label": "Broker 中转", "style": "dashed", "direction": "event"})
    connections.append({"from": "mqtt_model", "to": "coap_model", "label": "Broker 中转", "style": "dashed", "direction": "event"})
    return connections


def _protocol_regions(components: list[dict[str, str]]) -> list[dict[str, str]]:
    groups = [component.get("group", "") for component in components]
    if not any(group.startswith("protocol_") for group in groups):
        return []
    regions: list[dict[str, str]] = []
    for protocol in ["http", "mqtt", "coap"]:
        group = f"protocol_{protocol}"
        if group in groups:
            regions.append({"id": group, "label": protocol.upper() if protocol != "coap" else "CoAP", "role": _region_role(group)})
    return regions


def _component_items(value: object) -> list[dict[str, str]]:
    items = []
    for index, item in enumerate(_dict_items(value), start=1):
        label = _short(_scalar(item.get("label")) or _scalar(item.get("name")) or _scalar(item.get("id")) or f"组件{index}", 20)
        text = " ".join([label, _scalar(item.get("subtitle")), _scalar(item.get("role")), _scalar(item.get("type"))])
        group = _scalar(item.get("group")) or _infer_component_group(text)
        items.append(
            {
                "id": _component_id(_scalar(item.get("id")), index),
                "label": _clean_label(label),
                "type": _scalar(item.get("type")) or _infer_component_type(text),
                "subtitle": _short(_scalar(item.get("subtitle")) or _scalar(item.get("role")), 24),
                "group": group,
                "priority": _scalar(item.get("priority")) or "normal",
                "shape": _scalar(item.get("shape")) or _infer_shape(text),
            }
        )
    return items


def _connection_items(value: object, components: list[dict[str, str]]) -> list[dict[str, str]]:
    lookup = _component_lookup(components)
    items = []
    for item in _dict_items(value):
        source, target, parsed_label = _relationship_endpoints_from_dict(item)
        if not _valid_endpoint(source) or not _valid_endpoint(target):
            continue
        label = _scalar(item.get("label") or item.get("type") or item.get("condition")) or parsed_label or "主链路"
        source_id = lookup.get(source) or lookup.get(_strip_parenthetical(source)) or _safe_id(source)
        target_id = lookup.get(target) or lookup.get(_strip_parenthetical(target)) or _safe_id(target)
        if not source_id or not target_id:
            continue
        items.append(
            {
                "from": source_id,
                "to": target_id,
                "label": _edge_label(label) or "主链路",
                "style": _edge_style_from_raw(_scalar(item.get("style") or item.get("arrow") or item.get("arrow_type")), label),
                "direction": _scalar(item.get("direction")) or _direction_from_style(label),
            }
        )
    return items


def _components_from_structured_relationships(value: object) -> list[dict[str, str]]:
    endpoints: list[str] = []
    for item in _dict_items(value):
        source, target, _label = _relationship_endpoints_from_dict(item)
        for endpoint in [source, target]:
            if _valid_endpoint(endpoint) and not _endpoint_is_generic(endpoint) and endpoint not in endpoints:
                endpoints.append(endpoint)
    return [_component_from_endpoint(endpoint, index) for index, endpoint in enumerate(endpoints[:10], start=1)]


def _relationship_endpoints_from_dict(item: dict[str, Any]) -> tuple[str, str, str]:
    source = _scalar(item.get("from") or item.get("source"))
    target = _scalar(item.get("to") or item.get("target"))
    label = _scalar(item.get("label") or item.get("type") or item.get("condition"))
    if source and target:
        return source, target, label
    if source:
        parsed = _parse_relationship_string(source)
        if parsed is not None:
            parsed_source, parsed_target, parsed_label = parsed
            return parsed_source, parsed_target, label or parsed_label
    return source, target, label


def _components_from_relationship_endpoints(relationships: list[str]) -> list[dict[str, str]]:
    endpoints: list[str] = []
    for relationship in relationships:
        parsed = _parse_relationship_string(relationship)
        if parsed is None:
            continue
        source, target, _label = parsed
        for endpoint in [source, target]:
            if endpoint and endpoint not in endpoints:
                endpoints.append(endpoint)
    return [_component_from_endpoint(endpoint, index) for index, endpoint in enumerate(endpoints[:10], start=1)]


def _connections_from_relationship_strings(relationships: list[str], components: list[dict[str, str]]) -> list[dict[str, str]]:
    lookup = _component_lookup(components)
    items: list[dict[str, str]] = []
    for relationship in relationships:
        parsed = _parse_relationship_string(relationship)
        if parsed is None:
            continue
        source, target, label = parsed
        source_id = lookup.get(source, _safe_id(source))
        target_id = lookup.get(target, _safe_id(target))
        if not source_id or not target_id:
            continue
        items.append(
            {
                "from": source_id,
                "to": target_id,
                "label": _edge_label(label or relationship) or "主链路",
                "style": _edge_style(label or relationship),
                "direction": _direction_from_style(label or relationship),
            }
        )
    return items


def _parse_relationship_string(value: str) -> tuple[str, str, str] | None:
    text = str(value).strip()
    match = re.match(r"^(.+?)\s*(<->|↔|→|->|到|连接|接入|调用|流向)\s*(.+?)(?:[（(](.+?)[）)])?$", text)
    if not match:
        return None
    source = _short(match.group(1), 22)
    arrow = match.group(2)
    target = _short(match.group(3), 22)
    label = _short(match.group(4) or ("双向" if arrow in {"<->", "↔"} else ""), 24)
    if not _valid_endpoint(source) or not _valid_endpoint(target) or _endpoint_is_generic(source) or _endpoint_is_generic(target):
        return None
    return source, target, label


def _component_from_endpoint(endpoint: str, index: int) -> dict[str, str]:
    text = _clean_generic_references(endpoint)
    return {
        "id": f"r{index}",
        "label": _clean_label(text),
        "type": _infer_component_type(text),
        "subtitle": "",
        "group": _infer_component_group(text),
        "priority": "primary" if index == 1 else "normal",
        "shape": _infer_shape(text),
    }


def _components_look_too_generic(components: list[dict[str, str]]) -> bool:
    if not components:
        return False
    generic = 0
    for component in components:
        label = component.get("label", "")
        if _is_generic_label(label) or label.lower() in {"layer", "node", "component"} or len(label) > 24:
            generic += 1
    return generic >= max(1, len(components) // 2)


def _valid_endpoint(value: str) -> bool:
    text = value.strip()
    return bool(text) and text not in {"-", "—", "–", ""}


def _endpoint_is_generic(value: str) -> bool:
    text = value.strip()
    return bool(re.search(r"(?:节点|决策节点|判断节点|处理节点)\d+", text)) or text in {"最右侧", "左侧", "右侧"}


def _region_items(value: object) -> list[dict[str, str]]:
    items = []
    for index, item in enumerate(_dict_items(value), start=1):
        label = _scalar(item.get("label") or item.get("name")) or f"边界{index}"
        region_id = _scalar(item.get("id")) or _infer_component_group(label)
        items.append({"id": _safe_id(region_id) or f"region_{index}", "label": _short(label, 18), "role": _short(_scalar(item.get("role")), 24)})
    return items


def _component_from_participant(item: dict[str, Any], index: int) -> dict[str, str]:
    name = _scalar(item.get("name")) or f"参与者{index}"
    role = _scalar(item.get("role"))
    component_type = _infer_component_type(" ".join([name, role]))
    return {
        "id": f"p{index}",
        "label": _clean_label(name),
        "type": component_type,
        "subtitle": _short(role, 24),
        "group": _infer_component_group(" ".join([name, role])),
        "priority": "primary" if index == 2 else "normal",
        "shape": "actor" if index == 1 else "card",
    }


def _component_from_layer(item: dict[str, Any], index: int) -> dict[str, str]:
    label = _scalar(item.get("layer") or item.get("label") or item.get("name")) or f"层级{index}"
    subtitle = _scalar(item.get("description")) or "、".join(_string_items(item.get("elements"))[:3])
    text = " ".join([label, subtitle])
    return {
        "id": f"layer_{index}",
        "label": _clean_label(label),
        "type": _infer_component_type(text),
        "subtitle": _short(subtitle, 28),
        "group": _infer_component_group(text),
        "priority": "primary" if index == 1 else "normal",
        "shape": "card",
    }


def _component_from_node(item: dict[str, Any], index: int) -> dict[str, str]:
    label = _scalar(item.get("label") or item.get("name") or item.get("field") or item.get("item") or item.get("id")) or f"节点{index}"
    note = _scalar(item.get("note") or item.get("description") or item.get("explanation") or item.get("type"))
    text = " ".join([label, note])
    return {
        "id": _component_id(_scalar(item.get("id")), index),
        "label": _clean_label(label),
        "type": _infer_component_type(text),
        "subtitle": _short(note, 24),
        "group": _infer_component_group(text),
        "priority": "primary" if index == 1 else "normal",
        "shape": _scalar(item.get("shape")) or _infer_shape(text),
    }


def _component_from_text(value: str, index: int, *, figure_type: str) -> dict[str, str]:
    label, subtitle = _label_and_subtitle(value)
    text = " ".join([label, subtitle, value])
    return {
        "id": f"c{index}",
        "label": _clean_label(label),
        "type": _infer_component_type(text),
        "subtitle": _short(subtitle, 28),
        "group": _infer_component_group(text),
        "priority": "primary" if index == 1 or any(key in text for key in ["核心", "AI", "Agent", "智能", "关键"]) else "normal",
        "shape": "decision" if figure_type == "flowchart" and any(key in text for key in ["是否", "判断", "决策", "？", "?"]) else _infer_shape(text),
    }


def _label_and_subtitle(value: str) -> tuple[str, str]:
    text = str(value).replace("“", "‘").replace("”", "’").strip()
    prefix = ""
    suffix = text
    match = re.match(r"^([^:：]{1,28})[:：]\s*(.+)$", text)
    if match:
        prefix = match.group(1).strip()
        suffix = match.group(2).strip()
    quoted = _first_quoted(suffix)
    if prefix and _is_generic_label(prefix):
        label = quoted or _first_clause(suffix)
        subtitle = _role_from_suffix(suffix, label)
        return _short(label, 20), _short(subtitle, 30)
    if prefix:
        return _short(prefix, 20), _short(_role_from_suffix(suffix, quoted), 30)
    label = quoted or _first_clause(text)
    return _short(label, 20), _short(_role_from_suffix(text, label), 30)


def _audience_takeaway(title: str, purpose: str) -> str:
    # 优先复用 brief 的具体 purpose，避免退化成与图无关的通用套话。
    concrete = purpose.strip()
    if concrete:
        return _short(concrete, 60)
    subject = re.sub(r"^[图表]\d+[-—]\d+\s*", "", title).strip()
    return _short(subject, 60) if subject else ""


def _visual_focus(components: list[dict[str, str]], connections: list[dict[str, str]], purpose: str) -> str:
    if connections and components:
        by_id = {item["id"]: item["label"] for item in components}
        first = connections[0]
        last = connections[-1]
        return f"从{by_id.get(first.get('from', ''), '起点')}到{by_id.get(last.get('to', ''), '终点')}的主链路。"
    return _short(purpose, 48)


def _design_level(figure_type: str) -> str:
    if figure_type in {"architecture", "topology", "layered"}:
        return "logical"
    if figure_type in {"sequence", "flowchart", "dataflow", "lifecycle", "timeline"}:
        return "implementation"
    if figure_type in {"matrix", "pyramid"}:
        return "decision"
    return "conceptual"


def _split_relationship_sentences(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        parts = [part.strip() for part in re.split(r"[；;]\s*", item) if part.strip()]
        result.extend(parts or [item])
    return result[:12]


def _relationship_from_dict(item: dict[str, Any]) -> str:
    source, target, label = _relationship_endpoints_from_dict(item)
    if source and target:
        return f"{source} → {target}" + (f"（{label}）" if label else "")
    return label


def _string_items(value: object) -> list[str]:
    if isinstance(value, str):
        return [normalize_book_figure_scalar(value)] if value.strip() else []
    if isinstance(value, dict):
        return [f"{_scalar(key)}={_scalar(raw)}" for key, raw in value.items() if _scalar(raw)]
    if isinstance(value, list):
        items = []
        for item in value:
            text = _relationship_from_dict(item) or _dict_summary(item) if isinstance(item, dict) else _scalar(item)
            if text:
                items.append(text)
        return items
    return []


def _dict_items(value: object) -> list[dict[str, Any]]:
    return [item for item in _list_items(value) if isinstance(item, dict)]


def _list_items(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _dict_summary(item: dict[str, Any]) -> str:
    label = _scalar(item.get("label") or item.get("name") or item.get("layer") or item.get("field") or item.get("item") or item.get("id"))
    note = _scalar(item.get("note") or item.get("description") or item.get("role") or item.get("meaning") or item.get("explanation"))
    if label and note:
        return f"{label}: {note}"
    return label or note


def _nested_layer_items(value: object) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for item in _dict_items(value):
        side = _layer_side_label(_scalar(item.get("side") or item.get("name") or item.get("label")))
        layers = _dict_items(item.get("layers"))
        for layer in layers:
            name = _scalar(layer.get("name") or layer.get("label"))
            if name:
                result.append((side, name))
    return result


def _layer_side_label(value: str) -> str:
    text = value.strip().lower()
    if text == "left":
        return "四层"
    if text == "right":
        return "五层"
    return value.strip() or "分层"


def _component_lookup(components: list[dict[str, str]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for component in components:
        component_id = component["id"]
        for key in [component_id, component.get("label", ""), component.get("subtitle", "")]:
            if key:
                lookup[key] = component_id
                simplified = _strip_parenthetical(key)
                if simplified:
                    lookup[simplified] = component_id
    return lookup


def _infer_component_type(text: str) -> str:
    if any(key in text for key in ["设备", "边缘", "传感", "网关", "PLC", "采集", "现场"]):
        return "edge"
    if any(key in text for key in ["数据", "存储", "时序", "湖仓", "数据库", "Data"]):
        return "data"
    if any(key in text for key in ["AI", "Agent", "智能", "推理", "模型", "决策", "LLM"]):
        return "ai"
    if any(key in text for key in ["安全", "权限", "认证", "审计", "告警", "风险", "异常"]):
        return "security"
    if any(key in text for key in ["应用", "业务", "运营", "用户", "场景"]):
        return "application"
    if any(key in text for key in ["外部", "第三方", "供应商"]):
        return "external"
    if any(key in text for key in ["是否", "判断", "决策", "？", "?"]):
        return "decision"
    return "platform"


def _infer_component_group(text: str) -> str:
    component_type = _infer_component_type(text)
    return {
        "edge": "edge_domain",
        "data": "data_domain",
        "ai": "intelligence_domain",
        "security": "governance_domain",
        "application": "application_domain",
        "external": "external_domain",
        "decision": "decision_domain",
    }.get(component_type, "platform_domain")


def _infer_shape(text: str) -> str:
    if any(key in text for key in ["是否", "判断", "决策", "？", "?"]):
        return "decision"
    if any(key in text for key in ["数据库", "存储", "数据"]):
        return "database"
    if any(key in text for key in ["用户", "调度器", "参与者"]):
        return "actor"
    if any(key in text for key in ["消息", "队列", "总线", "MQTT", "Kafka"]):
        return "bus"
    return "card"


def _region_label(group: str) -> str:
    return {
        "edge_domain": "设备与边缘域",
        "platform_domain": "平台服务域",
        "data_domain": "数据资产域",
        "intelligence_domain": "智能决策域",
        "governance_domain": "治理与安全域",
        "application_domain": "业务应用域",
        "external_domain": "外部系统域",
        "decision_domain": "决策判断域",
        "protocol_http": "HTTP 协议列",
        "protocol_mqtt": "MQTT 协议列",
        "protocol_coap": "CoAP 协议列",
    }.get(group, group)


def _region_role(group: str) -> str:
    return {
        "edge_domain": "现场异构资源边界",
        "platform_domain": "核心服务能力边界",
        "data_domain": "数据沉淀与治理边界",
        "intelligence_domain": "模型、规则与 Agent 边界",
        "governance_domain": "风险控制与责任边界",
        "application_domain": "业务价值交付边界",
        "external_domain": "外部依赖与集成边界",
        "decision_domain": "判断条件与分支边界",
        "protocol_http": "Web API 与网关北向通信",
        "protocol_mqtt": "Broker 中转与双向消息",
        "protocol_coap": "受限设备低功耗通信",
    }.get(group, "语义分组边界")


def _edge_label(value: str) -> str:
    text = _clean_generic_references(_short(value, 36))
    text = re.sub(r"^(?:是|否)?\s*[→-]+\s*", "", text).strip()
    if re.fullmatch(r"(?:是|否)?\s*(?:进入下一判断|推荐路径)", text):
        return "是" if "是" in value else "下一步"
    return _short(text, 18)


def _edge_style(label: str) -> str:
    if any(key in label for key in ["响应", "返回", "虚线", "异步", "事件", "可选"]):
        return "dashed"
    if any(key in label for key in ["风险", "异常", "告警", "失败"]):
        return "risk"
    return "solid"


def _edge_style_from_raw(value: str, label: str) -> str:
    text = " ".join([value, label]).lower()
    if any(key in text for key in ["dashed", "虚线", "async", "event"]):
        return "dashed"
    if any(key in text for key in ["risk", "red", "danger", "失败", "风险", "异常", "告警"]):
        return "risk"
    if any(key in text for key in ["optional", "可选"]):
        return "optional"
    return _edge_style(label)


def _direction_from_style(label: str) -> str:
    if any(key in label for key in ["响应", "返回"]):
        return "response"
    if any(key in label for key in ["事件", "告警", "异步"]):
        return "event"
    return "request"


def _clean_label(value: str) -> str:
    text = _clean_generic_references(value)
    if _is_generic_label(text):
        return "关键判断"
    return _short(text, 18)


def _clean_generic_references(value: str) -> str:
    text = re.sub(r"(?:进入|转入|指向|到)?(?:节点|决策节点|判断节点|处理节点)\d+", "进入下一判断", str(value))
    text = re.sub(r"最右侧(?:路径)?", "推荐路径", text)
    return text.strip(" ，。；;：:、")


def _is_generic_label(value: str) -> bool:
    return bool(_GENERIC_LABEL_RE.fullmatch(value.strip()))


def _role_from_suffix(suffix: str, label: str) -> str:
    text = suffix.replace(label, "", 1).strip(" ，。；;：:—-、") if label else suffix
    for separator in ["——", "--", "—", "；", ";", "。"]:
        if separator in suffix:
            tail = suffix.split(separator, 1)[1].strip()
            if tail:
                return _clean_generic_references(tail)
    return _clean_generic_references(text)


def _first_quoted(value: str) -> str:
    match = re.search(r"[‘'\"]([^‘'\"]{3,80})[’'\"]", value)
    return match.group(1).strip() if match else ""


def _first_clause(value: str) -> str:
    text = value.strip(" ，。；;：:—-")
    for separator in ["——", "--", "—", "；", ";", "。", "，"]:
        if separator in text:
            text = text.split(separator, 1)[0]
            break
    return text.strip(" ，。；;：:—-")


def _scalar(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return "；".join(f"{_scalar(key)}={_scalar(raw)}" for key, raw in value.items() if _scalar(raw))
    if isinstance(value, list):
        return "；".join(_scalar(item) for item in value if _scalar(item))
    return normalize_book_figure_scalar(value)


def _key(value: object) -> str:
    return normalize_book_figure_scalar(value)


def _short(value: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip(" ，。；;：:、")
    return text if len(text) <= limit else text[: limit - 1].rstrip(" ，。；;：:、") + "…"


def _component_id(value: str, index: int) -> str:
    return _safe_id(value) or f"c{index}"


def _safe_id(value: str) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9_-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text if re.search(r"[a-z0-9]", text) else ""


def _strip_parenthetical(value: str) -> str:
    return re.sub(r"[（(].*?[）)]", "", value).strip()


def _figure_id_from_title(value: str, occurrence: int) -> str:
    match = re.search(r"([图表])\s*(\d+)\s*[-—]\s*(\d+)", value)
    if match:
        prefix = "tbl" if match.group(1) == "表" else "fig"
        return f"{prefix}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    return f"fig-auto-{occurrence:02d}"


def _regex_field(body: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*[\"“]?{re.escape(key)}[\"”]?\s*:\s*(.+?)\s*$", body)
    return normalize_book_figure_scalar(match.group(1).rstrip(",")) if match else ""


def _regex_list_block(body: str, key: str) -> list[str]:
    match = re.search(rf"(?ms)^\s*{re.escape(key)}\s*:\s*\n(?P<body>(?:\s+-\s+.+\n?)+)", body)
    if not match:
        return []
    return [normalize_book_figure_scalar(line.split("-", 1)[1]) for line in match.group("body").splitlines() if "-" in line]


def _quote_yaml(value: str) -> str:
    return str(yaml.safe_dump(str(value).strip(), allow_unicode=True, default_style='"')).strip()


def _dump_yaml(payload: dict[str, Any]) -> str:
    return str(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=120, default_flow_style=False))
