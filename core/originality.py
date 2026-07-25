"""原创性检测：把正文按段落切分，与参考原文做字符 n-gram 重叠度比对。

用于出版前的近似抄袭/洗稿检测：正文段落若与某本参考书原文的字符 n-gram
高度重叠，说明只是「贴着原文改」，需要重写。纯确定性算法，不依赖 LLM。
中文用字符 n-gram（而非词 n-gram）以规避分词依赖，对中文更稳。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_ATX_HEADING_RE = re.compile(r"^ {0,3}(?P<marks>#{1,6})(?:[ \t]+|$)(?P<title>.*)$")
_SECTION_ID_RE = re.compile(r"^(?P<section_id>\d+\.\d+\.\d+)(?:[ \t]+|$)")
_FENCE_RE = re.compile(r"^ {0,3}(?P<marks>`{3,}|~{3,}).*$")
_SKIP_PREFIXES = ("|", ">")


@dataclass
class SimilarityHit:
    """一段正文与某个参考来源的相似命中。"""

    paragraph_excerpt: str
    source_file: str
    overlap: float
    matched_excerpt: str


@dataclass(frozen=True)
class MarkdownParagraph:
    """代码围栏外的正文段落及其所属三级小节。"""

    text: str
    section_id: str = ""


def split_paragraphs(markdown: str) -> list[str]:
    """按自然段落切分正文，跳过标题/表格/代码块围栏等非正文行。"""
    return [paragraph.text for paragraph in split_paragraphs_with_sections(markdown)]


def split_paragraphs_with_sections(markdown: str) -> list[MarkdownParagraph]:
    """切分正文段落，并根据 H3 标题记录所属三级小节。"""
    paragraphs: list[MarkdownParagraph] = []
    current_lines: list[str] = []
    current_section_id = ""
    active_fence: tuple[str, int] | None = None

    def flush_paragraph() -> None:
        if not current_lines:
            return
        text = "\n".join(current_lines).strip()
        current_lines.clear()
        if text:
            paragraphs.append(MarkdownParagraph(text=text, section_id=current_section_id))

    for line in markdown.splitlines():
        fence = _FENCE_RE.match(line)
        if active_fence is not None:
            if fence is not None:
                marks = fence.group("marks")
                if marks[0] == active_fence[0] and len(marks) >= active_fence[1]:
                    active_fence = None
            continue
        if fence is not None:
            flush_paragraph()
            marks = fence.group("marks")
            active_fence = (marks[0], len(marks))
            continue

        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            continue
        heading = _ATX_HEADING_RE.match(line)
        if heading is not None:
            flush_paragraph()
            if len(heading.group("marks")) == 3:
                section_match = _SECTION_ID_RE.match(heading.group("title").strip())
                if section_match is not None:
                    current_section_id = section_match.group("section_id")
            continue
        if stripped.startswith(_SKIP_PREFIXES):
            flush_paragraph()
            continue
        current_lines.append(line)

    flush_paragraph()
    return paragraphs


def _char_ngrams(text: str, n: int) -> set[str]:
    """提取字符 n-gram 集合；剥离空白以免排版差异影响重叠计算。"""
    compact = re.sub(r"\s+", "", text)
    if len(compact) < n:
        return {compact} if compact else set()
    return {compact[i : i + n] for i in range(len(compact) - n + 1)}


def char_ngram_overlap(candidate: str, reference: str, n: int = 5) -> float:
    """候选段落被参考原文覆盖的比例：|A∩B| / |A|。

    分母取候选段落自身的 n-gram 数，衡量「这段有多少是照搬自参考原文的」，
    不受参考原文长度影响。返回 0.0~1.0。
    """
    cand_grams = _char_ngrams(candidate, n)
    if not cand_grams:
        return 0.0
    ref_grams = _char_ngrams(reference, n)
    if not ref_grams:
        return 0.0
    return len(cand_grams & ref_grams) / len(cand_grams)
