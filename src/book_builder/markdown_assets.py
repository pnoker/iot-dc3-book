"""Markdown 结构与资产扫描工具。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_PLACEHOLDER_IMAGE_RE = re.compile(r"^\s*!\[[^\]]+\]\s*$", re.MULTILINE)
_HEADING_RE = re.compile(r"^#{1,6}\s+.+$", re.MULTILINE)
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", re.MULTILINE)
_BOOK_FIGURE_RE_TEMPLATE = r"```{marker}\s*\n(?P<body>.*?)\n```"
_BOOK_FIGURE_REQUIRED_FIELDS = [
    "id",
    "type",
    "title",
    "purpose",
    "layout",
    "elements",
    "relationships",
    "legend",
    "caption",
    "render_notes",
]
_EDGE_QUOTES = "\"'“”‘’`"


@dataclass(frozen=True)
class MarkdownImage:
    """Markdown 图片引用。"""

    alt: str
    target: str

    @property
    def is_remote(self) -> bool:
        target = self.target.lower()
        return target.startswith(("http" + "://", "https" + "://", "data:"))


@dataclass(frozen=True)
class BookFigureSpec:
    """后续 HTML/SVG 绘制的图表规格块。"""

    body: str
    marker: str = "book-figure"


@dataclass(frozen=True)
class BookFigureBlock(BookFigureSpec):
    """带源码位置的图表规格块。"""

    start: int = 0
    end: int = 0


def extract_images(markdown: str) -> list[MarkdownImage]:
    """提取 Markdown 图片引用。"""
    return [MarkdownImage(alt=match.group(1).strip(), target=match.group(2).strip()) for match in _IMAGE_RE.finditer(markdown)]


def find_placeholder_images(markdown: str) -> list[str]:
    """查找没有目标路径的图片占位行。"""
    return [match.group(0).strip() for match in _PLACEHOLDER_IMAGE_RE.finditer(markdown)]


def extract_book_figures(markdown: str, marker: str = "book-figure") -> list[BookFigureSpec]:
    """提取图表规格块。"""
    return [BookFigureSpec(body=block.body, marker=marker) for block in iter_book_figure_blocks(markdown, marker)]


def iter_book_figure_blocks(markdown: str, marker: str = "book-figure") -> list[BookFigureBlock]:
    """按正文顺序返回带位置的图表规格块。"""
    pattern = re.compile(_BOOK_FIGURE_RE_TEMPLATE.format(marker=re.escape(marker)), re.DOTALL)
    return [
        BookFigureBlock(body=match.group("body").strip(), marker=marker, start=match.start(), end=match.end())
        for match in pattern.finditer(markdown)
    ]


def find_invalid_book_figures(
        markdown: str,
        marker: str = "book-figure",
        required_fields: list[str] | None = None,
        allowed_types: list[str] | None = None,
) -> list[str]:
    """返回不符合出版图表规格的说明。"""
    required = required_fields or _BOOK_FIGURE_REQUIRED_FIELDS
    allowed = {normalize_book_figure_scalar(item).lower() for item in allowed_types or []}
    invalid: list[str] = []
    for index, figure in enumerate(extract_book_figures(markdown, marker), start=1):
        payload, reason = parse_book_figure_payload(figure.body)
        if payload is None:
            invalid.append(f"第{index}个 `{marker}` 无法解析: {reason}")
            continue
        missing = [field for field in required if field not in payload or payload.get(field) in (None, "", [])]
        if missing:
            invalid.append(f"第{index}个 `{marker}` 缺少字段: {', '.join(missing)}")
            continue
        figure_type = normalize_book_figure_scalar(payload.get("type", "")).lower()
        if allowed and figure_type not in allowed:
            invalid.append(f"第{index}个 `{marker}` 不支持 type: {figure_type}；允许: {', '.join(sorted(allowed))}")
            continue
        quality_issues = _book_figure_design_quality_issues(payload)
        if quality_issues:
            invalid.append(f"第{index}个 `{marker}` 设计规格不达出版级: {'; '.join(quality_issues[:3])}")
    return invalid


def parse_book_figure_payload(body: str) -> tuple[dict[str, Any] | None, str]:
    """解析并规范化 `book-figure` YAML/JSON 规格块。"""
    try:
        raw = yaml.safe_load(body)
    except yaml.YAMLError as exc:
        return None, f"YAML 解析失败: {exc}"
    if not isinstance(raw, dict):
        return None, "规格块必须是 YAML 对象"

    payload: dict[str, Any] = {}
    for key, value in raw.items():
        normalized_key = normalize_book_figure_scalar(key)
        if not normalized_key:
            continue
        payload[normalized_key] = _normalize_book_figure_value(value)
    return payload, ""


def _normalize_book_figure_value(value: object) -> object:
    if isinstance(value, str):
        return normalize_book_figure_scalar(value)
    if isinstance(value, list):
        normalized: list[object] = []
        for item in value:
            normalized_item = _normalize_book_figure_value(item)
            if normalized_item in (None, "", []):
                continue
            normalized.append(normalized_item)
        return normalized
    if isinstance(value, dict):
        normalized_dict: dict[str, object] = {}
        for key, item in value.items():
            normalized_key = normalize_book_figure_scalar(key)
            if not normalized_key:
                continue
            normalized_value = _normalize_book_figure_value(item)
            if normalized_value in (None, "", []):
                continue
            normalized_dict[normalized_key] = normalized_value
        return normalized_dict
    return value


def normalize_book_figure_scalar(value: object) -> str:
    """清理 AI 输出中常见的边界引号，保留正文语义。"""
    text = str(value).strip()
    if len(text) >= 2 and text[0] in _EDGE_QUOTES and text[-1] in _EDGE_QUOTES:
        return text[1:-1].strip()
    return text


def book_figure_string_list(value: object) -> list[str]:
    """把图表元素、关系、图例字段规范成字符串列表。"""
    if isinstance(value, list):
        return [normalized for item in value if isinstance(item, str) and (normalized := normalize_book_figure_scalar(item))]
    if isinstance(value, str) and value.strip():
        return [normalize_book_figure_scalar(value)]
    return []


def _book_figure_design_quality_issues(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    components = _payload_dict_items(payload.get("components"))
    connections = _payload_dict_items(payload.get("connections"))
    if components and not _has_semantic_components(components):
        issues.append("components 缺少可识别的 id/label/type/group 语义")
    if connections and not _has_semantic_connections(connections):
        issues.append("connections 缺少 from/to/label 结构化关系")
    elements = book_figure_string_list(payload.get("elements"))
    relationships = book_figure_string_list(payload.get("relationships"))
    if not components and _looks_like_placeholder_list(elements):
        issues.append("elements 仍是节点占位或长句描述，需拆成 components")
    if not connections and _looks_like_unstructured_relationships(relationships):
        issues.append("relationships 仍是一句话串联多条边，需拆成 connections")
    return issues


def _payload_dict_items(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _has_semantic_components(items: list[dict[str, object]]) -> bool:
    semantic_count = 0
    for item in items:
        label = normalize_book_figure_scalar(item.get("label", ""))
        type_ = normalize_book_figure_scalar(item.get("type", ""))
        group = normalize_book_figure_scalar(item.get("group", ""))
        if label and not _is_generic_figure_label(label) and (type_ or group):
            semantic_count += 1
    return semantic_count >= min(2, len(items))


def _has_semantic_connections(items: list[dict[str, object]]) -> bool:
    semantic_count = 0
    for item in items:
        source = normalize_book_figure_scalar(item.get("from", ""))
        target = normalize_book_figure_scalar(item.get("to", ""))
        label = normalize_book_figure_scalar(item.get("label", ""))
        if source and target and label and source != target:
            semantic_count += 1
    return semantic_count >= min(1, len(items))


def _looks_like_placeholder_list(items: list[str]) -> bool:
    if not items:
        return False
    generic_count = sum(1 for item in items if _is_generic_figure_label(item.split("：", 1)[0].split(":", 1)[0]))
    long_sentence_count = sum(1 for item in items if len(item) > 80 or item.count("；") >= 2)
    return generic_count >= 2 or long_sentence_count >= max(2, len(items) // 2 + 1)


def _looks_like_unstructured_relationships(items: list[str]) -> bool:
    return any(item.count("；") >= 2 or item.count("->") >= 2 or item.count("→") >= 3 for item in items)


def _is_generic_figure_label(value: str) -> bool:
    text = normalize_book_figure_scalar(value)
    return bool(re.fullmatch(r"(?:节点|决策节点|判断节点|处理节点|计算节点|执行节点|开始节点|结束状态|输入数据源|输出节点|最左侧|最右侧|左侧|右侧)\d*", text))


def count_headings(markdown: str) -> int:
    """统计标题数量。"""
    return len(_HEADING_RE.findall(markdown))


def count_figures_or_tables(markdown: str, marker: str = "book-figure") -> int:
    """统计图或表的数量。"""
    image_count = len(extract_images(markdown)) + len(find_placeholder_images(markdown))
    book_figure_count = len(extract_book_figures(markdown, marker))
    table_count = len(_TABLE_SEPARATOR_RE.findall(markdown))
    table_caption_count = len(re.findall(r"(^|\n)\s*(表\d+[-—]\d+|\*?表\d+[-—]\d+)", markdown))
    return image_count + book_figure_count + table_count + table_caption_count


def missing_local_images(markdown: str, base_dir: Path | None = None) -> list[str]:
    """返回不存在的本地图片路径。"""
    root = (base_dir or Path.cwd()).resolve()
    missing: list[str] = []
    for image in extract_images(markdown):
        if image.is_remote:
            continue
        target = image.target.split("#", 1)[0].split("?", 1)[0]
        if not target:
            missing.append(image.target)
            continue
        path = Path(target)
        candidates = [path] if path.is_absolute() else [root / path, root / "output" / path]
        if not any(candidate.exists() for candidate in candidates):
            missing.append(image.target)
    return missing
