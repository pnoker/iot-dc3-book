"""Markdown 结构与资产扫描工具。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_PLACEHOLDER_IMAGE_RE = re.compile(r"^\s*!\[[^\]]+\]\s*$", re.MULTILINE)
_HEADING_RE = re.compile(r"^#{1,6}\s+.+$", re.MULTILINE)
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", re.MULTILINE)
_BOOK_FIGURE_RE_TEMPLATE = r"```{marker}\s*\n(?P<body>.*?)\n```"


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


def extract_images(markdown: str) -> list[MarkdownImage]:
    """提取 Markdown 图片引用。"""
    return [MarkdownImage(alt=match.group(1).strip(), target=match.group(2).strip()) for match in _IMAGE_RE.finditer(markdown)]


def find_placeholder_images(markdown: str) -> list[str]:
    """查找没有目标路径的图片占位行。"""
    return [match.group(0).strip() for match in _PLACEHOLDER_IMAGE_RE.finditer(markdown)]


def extract_book_figures(markdown: str, marker: str = "book-figure") -> list[BookFigureSpec]:
    """提取图表规格块。"""
    pattern = re.compile(_BOOK_FIGURE_RE_TEMPLATE.format(marker=re.escape(marker)), re.DOTALL)
    return [BookFigureSpec(body=match.group("body").strip(), marker=marker) for match in pattern.finditer(markdown)]


def find_invalid_book_figures(
        markdown: str,
        marker: str = "book-figure",
        required_fields: list[str] | None = None,
) -> list[str]:
    """返回缺少必填字段的图表规格块说明。"""
    required = required_fields or [
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
    invalid: list[str] = []
    for index, figure in enumerate(extract_book_figures(markdown, marker), start=1):
        missing = [field for field in required if not re.search(rf"^\s*{re.escape(field)}\s*:", figure.body, re.MULTILINE)]
        if missing:
            invalid.append(f"第{index}个 `{marker}` 缺少字段: {', '.join(missing)}")
    return invalid


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
