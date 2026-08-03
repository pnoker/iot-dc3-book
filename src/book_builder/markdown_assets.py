"""book-figure 规格块解析与规范化。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

_BOOK_FIGURE_RE_TEMPLATE = r"```{marker}\s*\n(?P<body>.*?)\n```"
_EDGE_QUOTES = "\"'“”‘’`"


@dataclass(frozen=True)
class BookFigureBlock:
    """带源码位置的图表规格块。"""

    body: str
    marker: str = "book-figure"
    start: int = 0
    end: int = 0


def iter_book_figure_blocks(markdown: str, marker: str = "book-figure") -> list[BookFigureBlock]:
    """按正文顺序返回带位置的图表规格块。"""
    pattern = re.compile(_BOOK_FIGURE_RE_TEMPLATE.format(marker=re.escape(marker)), re.DOTALL)
    return [
        BookFigureBlock(body=match.group("body").strip(), marker=marker, start=match.start(), end=match.end())
        for match in pattern.finditer(markdown)
    ]


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
