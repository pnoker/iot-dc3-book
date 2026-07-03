"""
Markdown 文本提取工具

面向 VitePress 文档：剥离 YAML frontmatter，清理容器标记与页面级脚本，
按标题切分为带 section 标签的块。产出结构与 rag_pdf 的 PdfPage 对齐
（unit/text/section），便于索引器统一处理。
"""

from __future__ import annotations

import re
from typing import TypedDict

import yaml

from core.log import get_logger

logger = get_logger("rag")

_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_CONTAINER_RE = re.compile(r"^\s*:::+")  # VitePress 容器标记 ::: / :::: …
_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
_BLOCK_TAG_RE = re.compile(r"^\s*</?(script|style)\b", re.IGNORECASE)
_TOC_RE = re.compile(r"^\s*\[\[toc\]\]\s*$", re.IGNORECASE)


class MarkdownSection(TypedDict):
    unit: int
    text: str
    section: str


def extract_markdown_sections(md_path: str) -> list[MarkdownSection]:
    """读取 Markdown，剥离 frontmatter 与噪音后按标题分段。"""
    with open(md_path, encoding="utf-8") as f:
        raw = f.read()

    body, default_section = _strip_frontmatter(raw)
    lines = _clean_lines(body.splitlines())
    return _segment_by_heading(lines, default_section)


def _strip_frontmatter(text: str) -> tuple[str, str]:
    """删除首部 YAML frontmatter，返回正文和从中解析出的默认 section（title）。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text, ""
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            front = "\n".join(lines[1:idx])
            body = "\n".join(lines[idx + 1:])
            return body, _parse_title(front)
    return text, ""  # 没有闭合的 ---，视为无 frontmatter


def _parse_title(front: str) -> str:
    try:
        data = yaml.safe_load(front)
    except yaml.YAMLError:
        return ""
    if isinstance(data, dict):
        title = data.get("title")
        if isinstance(title, str):
            return title.strip()
    return ""


def _clean_lines(lines: list[str]) -> list[str]:
    """代码围栏感知地清理噪音行：容器标记、页面级 script/style 块、TOC。

    行内标签（如 <br>、<String>、<host>）是正文的一部分（HTML/Java 泛型/URL 模板），
    不清理，以免破坏技术事实。仅清理独占一行的页面级块。
    """
    cleaned: list[str] = []
    in_fence = False
    in_block_tag = False
    for line in lines:
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            cleaned.append(line)
            continue
        if in_fence:
            cleaned.append(line)
            continue
        if in_block_tag:
            if re.search(r"</(script|style)>", line, re.IGNORECASE):
                in_block_tag = False
            continue
        if _BLOCK_TAG_RE.match(line):
            # 单行 <script>…</script> 或跨行块起始
            if not re.search(r"</(script|style)>", line, re.IGNORECASE):
                in_block_tag = True
            continue
        if _CONTAINER_RE.match(line) or _TOC_RE.match(line):
            continue
        cleaned.append(line)
    return cleaned


def _segment_by_heading(lines: list[str], default_section: str) -> list[MarkdownSection]:
    """按一~三级标题切块，每块 section 为其标题；首块用 frontmatter title。"""
    sections: list[MarkdownSection] = []
    current_section = default_section or "正文"
    buffer: list[str] = []
    unit = 0

    def flush() -> None:
        nonlocal unit
        text = "\n".join(buffer).strip()
        if text:
            sections.append({"unit": unit, "text": text, "section": current_section})
            unit += 1

    for line in lines:
        match = _HEADING_RE.match(line)
        if match:
            flush()
            current_section = match.group(2).strip()
            buffer = [line]
        else:
            buffer.append(line)
    flush()
    return sections
