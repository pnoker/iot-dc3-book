"""HTML 插图的出版前静态质量检查。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FigureAuditIssue:
    source: Path
    reason: str


_FIGURE_NUMBER_PATTERN = re.compile(r"图\s*(\d+)\s*[-—–]\s*(\d+)")
_FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r">\s*from:\s*[^<]+<", re.IGNORECASE),
    re.compile(r">\s*color:\s*#[^<]+<", re.IGNORECASE),
    re.compile(r"<script\b", re.IGNORECASE),
    re.compile(r"(?:src|href)=[\"']https?://", re.IGNORECASE),
    re.compile(r"letter-spacing\s*:\s*-", re.IGNORECASE),
)


def audit_figure_html(
    source_dir: str | Path,
    *,
    chapter: int | None = None,
    figure_id: str | None = None,
) -> list[FigureAuditIssue]:
    """检查图号、导出根和禁止出现在出版图中的实现残留。"""
    root = Path(source_dir)
    chapter_pattern = f"chapter-{chapter:02d}" if chapter is not None else "chapter-*"
    sources = sorted(root.glob(f"{chapter_pattern}/*.html"))
    if figure_id:
        sources = [source for source in sources if source.stem == figure_id]
    issues: list[FigureAuditIssue] = []
    for source in sources:
        text = source.read_text(encoding="utf-8")
        expected = _expected_number(source)
        root_count = len(re.findall(r"<[^>]+\sdata-figure-root(?:\s|>|=)", text))
        if root_count != 1:
            issues.append(FigureAuditIssue(source, "必须且只能有一个 data-figure-root"))
        if expected:
            found = {
                (int(chapter), int(number))
                for chapter, number in _FIGURE_NUMBER_PATTERN.findall(text)
            }
            unexpected = sorted(found - {expected})
            if unexpected:
                labels = "、".join(f"图{chapter}-{number}" for chapter, number in unexpected)
                issues.append(FigureAuditIssue(source, f"包含其他图号: {labels}"))
            if expected not in found:
                issues.append(
                    FigureAuditIssue(source, f"缺少图号: 图{expected[0]}-{expected[1]}")
                )
        for pattern in _FORBIDDEN_TEXT_PATTERNS:
            if pattern.search(text):
                issues.append(FigureAuditIssue(source, f"命中禁止模式: {pattern.pattern}"))
    return issues


def _expected_number(source: Path) -> tuple[int, int] | None:
    match = re.fullmatch(r"fig-(\d+)-(\d+)", source.stem)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))
