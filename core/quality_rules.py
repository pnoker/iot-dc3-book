"""出版级确定性质量门。"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel

from core.markdown_assets import (
    count_figures_or_tables,
    count_headings,
    extract_book_figures,
    find_invalid_book_figures,
    find_placeholder_images,
    missing_local_images,
)
from core.originality import char_ngram_overlap, split_paragraphs_with_sections
from core.state import BookState, ChapterContent, QualitySettings, SectionContent
from core.wordcount import count_words

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from core.rag import RAGEngine


class PublicationIssue(BaseModel):
    """确定性质量门问题。"""

    code: str
    severity: str = "major"
    scope: Literal["chapter", "section"] = "chapter"
    section_id: str = ""
    section_title: str = ""
    excerpt: str = ""
    message: str
    suggestion: str = ""


class PublicationQualityReport(BaseModel):
    """确定性质量门报告。"""

    pass_: bool
    issues: list[PublicationIssue]
    statistics: dict[str, Any]

    def to_feedback(self) -> str:
        """转为可写入 ChapterContent 的 JSON 反馈。"""
        return json.dumps(
            {
                "pass": self.pass_,
                "issues": [_issue_feedback_payload(issue) for issue in self.issues],
                "statistics": self.statistics,
            },
            ensure_ascii=False,
        )


def _issue_feedback_payload(issue: PublicationIssue) -> dict[str, object]:
    payload = issue.model_dump()
    if payload.get("scope") == "chapter":
        payload.pop("scope", None)
    for key in ["section_id", "section_title", "excerpt"]:
        if not payload.get(key):
            payload.pop(key, None)
    return payload


_CHAPTER_CLOSURE_RE = re.compile(
    r"(^|\n)#{2,4}\s*(?:\d+(?:\.\d+){1,2}\s*)?"
    r"(本章小结|小结|章节小结|本章核心要点|核心要点.*回顾|关键概念回顾|知识体系回顾|"
    r"工程检查(?:表|清单)|实践清单|实践边界|方法论回扣|趋势判断|延伸阅读)",
    re.MULTILINE,
)
_EXERCISE_RE = re.compile(r"(^|\n)##\s*(思考与练习|练习|实践练习)\s*$", re.MULTILINE)
_EXERCISE_ITEM_RE = re.compile(r"(^|\n)\s*(?:[-*+]\s+|\d+[.)、]\s+).+")
_VAGUE_STAT_RE = re.compile(
    r"(据行业调查|据相关调查|数据显示|统计显示|研究表明|有报告指出|超过[一二三四五六七八九十\d]+成|\d+(?:\.\d+)?%)"
)
_HARD_FACT_RE = re.compile(
    r"("
    r"(?:19|20)\d{2}\s*年"
    r"|Release\s*\d+"
    r"|\d+(?:\.\d+)?\s*(?:ms|毫秒|μs|us|秒|Mbps|Gbps|Kbps|kbps|MB/s|GB/s|TPS|QPS)"
    r"|\d+(?:\.\d+)?\s*(?:亿元|亿美元|万元|元|美元|RMB|CNY|USD)"
    r")",
    re.I,
)
_SOURCE_HINT_RE = re.compile(
    r"(Gartner|IDC|IEEE|ISO|IEC|3GPP|GSMA|工信部|报告《|来源[:：]|引用[:：]|资料[:：]|\[[SW]\d+\])",
    re.I,
)
_HYPOTHETICAL_HINT_RE = re.compile(r"(假设|示意|示例|例如|比如|建议|可设为|可以设为|取值|演示|样例)")
_CLAIM_BLOCK_SPLIT_RE = re.compile(r"\n\s*\n|(?=^\s*[-*+]\s+)", re.MULTILINE)
_CLAIM_HEADING_RE = re.compile(r"^ {0,3}(?P<marks>#{1,6})(?:[ \t]+|$)(?P<title>.*)$")
_CODE_FENCE_RE = re.compile(r"^ {0,3}(?P<marks>`{3,}|~{3,}).*$")


def evaluate_chapter_quality(
    state: BookState,
    content: ChapterContent,
    base_dir: Path | None = None,
) -> PublicationQualityReport:
    """执行非 LLM 的章节出版质量校验。"""
    settings = state.quality
    if not settings.enabled:
        return PublicationQualityReport(pass_=True, issues=[], statistics={"enabled": False})

    markdown = content.markdown
    illustration_cfg = state.style.illustrations or {}
    figure_marker = str(illustration_cfg.get("marker", "book-figure"))
    required_figure_fields = illustration_cfg.get("required_fields")
    if not isinstance(required_figure_fields, list):
        required_figure_fields = None
    allowed_figure_types = illustration_cfg.get("allowed_types")
    if not isinstance(allowed_figure_types, list):
        allowed_figure_types = None
    actual_words = count_words(markdown)
    target_words = max(settings.target_words_per_chapter, state.writing.target_for_chapter(content.chapter_id))
    max_words = int(target_words * settings.max_words_over_target_ratio) if settings.max_words_over_target_ratio else 0
    heading_count = count_headings(markdown)
    figure_or_table_count = count_figures_or_tables(markdown, marker=figure_marker)
    issues: list[PublicationIssue] = []

    _check_word_count(settings, actual_words, target_words, max_words, issues)
    _check_structure(settings, markdown, heading_count, figure_or_table_count, issues)
    _check_section_figures(state, content, figure_marker, issues)
    _check_book_figure_specs(markdown, figure_marker, required_figure_fields, allowed_figure_types, issues)
    _check_assets(settings, markdown, base_dir, issues)
    _check_unsourced_hard_facts(settings, state, content, issues)

    statistics = {
        "word_count": actual_words,
        "min_words": settings.min_words_per_chapter,
        "target_words": target_words,
        "max_words": max_words,
        "heading_count": heading_count,
        "figure_or_table_count": figure_or_table_count,
    }
    return PublicationQualityReport(pass_=not issues, issues=issues, statistics=statistics)


def ensure_book_releasable(state: BookState, base_dir: Path | None = None) -> None:
    """输出前校验整书是否达到发布条件。"""
    if not state.quality.enabled or state.quality.mode != "release":
        return
    if state.publication_approved:
        failed: list[str] = []
        for content in state.chapters:
            report = evaluate_chapter_quality(state, content, base_dir=base_dir)
            if not report.pass_:
                summary = "；".join(issue.message for issue in report.issues[:3])
                failed.append(f"第{content.chapter_id}章: {summary}")
        if failed:
            raise RuntimeError("出版级 release 输出前质量复检失败：" + " | ".join(failed[:5]))
        return
    raise RuntimeError("出版级 release 模式要求终审通过后才能输出。当前书稿尚未 publication_approved。")


def check_originality(
    rag: RAGEngine,
    content: ChapterContent,
    settings: QualitySettings,
    *,
    categories: Sequence[str] | None = None,
) -> list[PublicationIssue]:
    """检测章节正文是否与参考书原文（label=books）高度雷同，产出侵权风险问题。

    对每个正文段落检索最相似的参考原文，只对「别人写的」来源（label=books）计算字符
    n-gram 重叠；与自有内容（如 label=dc3）雷同不算侵权，直接放行。
    """
    if not settings.originality_check_enabled:
        return []

    issues: list[PublicationIssue] = []
    for index, located_paragraph in enumerate(split_paragraphs_with_sections(content.markdown), start=1):
        paragraph = located_paragraph.text
        if len(paragraph) < settings.originality_min_paragraph_chars:
            continue
        best_overlap = 0.0
        best_source = ""
        for hit in rag.retrieve_sparse(paragraph, top_k=3, categories=categories):
            if hit.label != "books":  # 只对别人写的材料判侵权；自有内容雷同放行
                continue
            overlap = char_ngram_overlap(paragraph, hit.text, n=settings.originality_ngram)
            if overlap > best_overlap:
                best_overlap = overlap
                best_source = hit.source_file
        if best_overlap >= settings.originality_max_overlap:
            location = (
                f"三级小节 {located_paragraph.section_id} 的第{index}段"
                if located_paragraph.section_id
                else f"第{index}段"
            )
            issues.append(
                PublicationIssue(
                    code="originality.suspected_copy",
                    scope="section" if located_paragraph.section_id else "chapter",
                    section_id=located_paragraph.section_id,
                    excerpt=paragraph[:200],
                    message=(
                        f"{location}与《{best_source}》字符 {settings.originality_ngram}-gram 重叠 "
                        f"{best_overlap:.0%}，疑似贴着原文改写，存在侵权风险。"
                    ),
                    suggestion="用自己的组织方式重写该段：改变论述结构、举例和措辞，而不是在原文上替换个别词。",
                )
            )
    return issues


def _check_word_count(
    settings: QualitySettings,
    actual_words: int,
    target_words: int,
    max_words: int,
    issues: list[PublicationIssue],
) -> None:
    if actual_words < settings.min_words_per_chapter:
        issues.append(
            PublicationIssue(
                code="word_count.too_short",
                message=f"章节正文字数 {actual_words}，低于出版下限 {settings.min_words_per_chapter}。",
                suggestion="按章节蓝图扩写案例、图表解释、工程步骤、风险分析和实践清单。",
            )
        )
    if max_words and actual_words > max_words:
        issues.append(
            PublicationIssue(
                code="word_count.too_long",
                message=f"章节正文字数 {actual_words}，超过目标 {target_words} 的上限 {max_words}。",
                suggestion="压缩重复论述、弱化旁支内容，优先保留证据充分的关键概念、工程步骤和图表解释。",
            )
        )


def _check_structure(
    settings: QualitySettings,
    markdown: str,
    heading_count: int,
    figure_or_table_count: int,
    issues: list[PublicationIssue],
) -> None:
    if heading_count < settings.min_heading_count:
        issues.append(
            PublicationIssue(
                code="structure.too_few_headings",
                message=f"标题数量 {heading_count}，低于出版级结构下限 {settings.min_heading_count}。",
                suggestion="补齐二级/三级小节，按问题、原理、工程实践、风险和小结展开。",
            )
        )
    if settings.require_summary and not _CHAPTER_CLOSURE_RE.search(markdown):
        issues.append(
            PublicationIssue(
                code="structure.missing_closure",
                message="缺少自然的章节收束。",
                suggestion="按内容需要增加方法论回扣、工程检查表、实践边界、趋势判断或延伸阅读；不要写课后练习式总结。",
            )
        )
    if settings.require_exercises:
        exercise_match = _EXERCISE_RE.search(markdown)
        exercise_count = len(_EXERCISE_ITEM_RE.findall(markdown[exercise_match.start() :])) if exercise_match else 0
        if not exercise_match or exercise_count < settings.min_exercise_count:
            issues.append(
                PublicationIssue(
                    code="structure.missing_exercises",
                    message=f"思考与练习不足，当前 {exercise_count} 题，要求至少 {settings.min_exercise_count} 题。",
                    suggestion="补充理解题、设计题、实践题和开放题。",
                )
            )
    if figure_or_table_count < settings.min_figures_or_tables:
        issues.append(
            PublicationIssue(
                code="asset.missing_figure_or_table",
                message=f"图表数量 {figure_or_table_count}，要求至少 {settings.min_figures_or_tables} 个。",
                suggestion="补充架构图、流程图、对比表或配置表，并在正文解释图表含义。",
            )
        )


def _check_section_figures(
    state: BookState,
    content: ChapterContent,
    marker: str,
    issues: list[PublicationIssue],
) -> None:
    min_figures = state.quality.min_figures_per_section
    if min_figures <= 0:
        return
    missing: list[str] = []
    for section in state.get_chapter_section_contents(content.chapter_id):
        figure_count = len(extract_book_figures(section.markdown, marker=marker))
        if figure_count < min_figures:
            missing.append(f"{section.section_id} {section.title}: {figure_count}/{min_figures}")
    if missing:
        issues.append(
            PublicationIssue(
                code="asset.section_missing_book_figure",
                message="以下三级小节缺少完整配图规格块: " + "；".join(missing[:10]),
                suggestion=f"每个三级小节至少补充 {min_figures} 个 `{marker}` 规格块，描述图表类型、元素、关系、图例、图注和 HTML/SVG 渲染说明。",
            )
        )


def _check_assets(
    settings: QualitySettings,
    markdown: str,
    base_dir: Path | None,
    issues: list[PublicationIssue],
) -> None:
    if settings.forbid_placeholder_images:
        placeholders = find_placeholder_images(markdown)
        if placeholders:
            issues.append(
                PublicationIssue(
                    code="asset.placeholder_image",
                    message=f"存在无路径图片占位: {'；'.join(placeholders[:3])}",
                    suggestion="删除占位或补齐真实图片路径/可生成的 Mermaid/SVG 图。",
                )
            )
    if settings.require_existing_local_images:
        missing = missing_local_images(markdown, base_dir)
        if missing:
            issues.append(
                PublicationIssue(
                    code="asset.missing_local_image",
                    message=f"本地图片不存在: {'；'.join(missing[:5])}",
                    suggestion="生成对应图片资源，或改为正文可渲染的 Mermaid/SVG/表格。",
                )
            )


def _check_book_figure_specs(
    markdown: str,
    marker: str,
    required_fields: list[str] | None,
    allowed_types: list[str] | None,
    issues: list[PublicationIssue],
) -> None:
    invalid = find_invalid_book_figures(
        markdown, marker=marker, required_fields=required_fields, allowed_types=allowed_types
    )
    if invalid:
        issues.append(
            PublicationIssue(
                code="asset.invalid_book_figure",
                message="图表规格块不完整: " + "；".join(invalid[:3]),
                suggestion=f"补齐 `{marker}` 规格块中的图名、用途、布局、元素、关系、图例、图注和渲染说明。",
            )
        )


def _check_unsourced_hard_facts(
    settings: QualitySettings,
    state: BookState,
    content: ChapterContent,
    issues: list[PublicationIssue],
) -> None:
    if not settings.forbid_unsourced_statistics:
        return
    section_contents = state.get_chapter_section_contents(content.chapter_id)
    if section_contents:
        for section_content in section_contents:
            vague_statistics, hard_facts = _unsourced_claim_excerpts(section_content.markdown)
            _append_unsourced_claim_issues(issues, vague_statistics, hard_facts, section_content=section_content)
        return

    vague_statistics, hard_facts = _unsourced_claim_excerpts(content.markdown)
    _append_unsourced_claim_issues(issues, vague_statistics, hard_facts, section_content=None)


def _unsourced_claim_excerpts(markdown: str) -> tuple[list[str], list[str]]:
    vague_statistics: list[str] = []
    hard_facts: list[str] = []
    hypothetical_heading_level: int | None = None
    prose_markdown = _strip_fenced_code_blocks(markdown)
    for paragraph in _CLAIM_BLOCK_SPLIT_RE.split(prose_markdown):
        stripped = paragraph.strip()
        heading = _CLAIM_HEADING_RE.match(stripped)
        if heading is not None:
            level = len(heading.group("marks"))
            if hypothetical_heading_level is not None and level <= hypothetical_heading_level:
                hypothetical_heading_level = None
            if _HYPOTHETICAL_HINT_RE.search(heading.group("title")):
                hypothetical_heading_level = level
            continue
        text = stripped.replace("\n", " ")
        if not text or text.startswith("|") or _SOURCE_HINT_RE.search(text):
            continue
        if hypothetical_heading_level is not None or _HYPOTHETICAL_HINT_RE.search(text):
            continue
        if _VAGUE_STAT_RE.search(text):
            vague_statistics.append(text[:120])
            continue
        if _HARD_FACT_RE.search(text):
            hard_facts.append(text[:120])
    return vague_statistics, hard_facts


def _strip_fenced_code_blocks(markdown: str) -> str:
    lines: list[str] = []
    active_fence: tuple[str, int] | None = None
    for line in markdown.splitlines():
        fence = _CODE_FENCE_RE.match(line)
        if active_fence is not None:
            if fence is not None:
                marks = fence.group("marks")
                if marks[0] == active_fence[0] and len(marks) >= active_fence[1]:
                    active_fence = None
            continue
        if fence is not None:
            marks = fence.group("marks")
            active_fence = (marks[0], len(marks))
            lines.append("")
            continue
        lines.append(line)
    return "\n".join(lines)


def _append_unsourced_claim_issues(
    issues: list[PublicationIssue],
    vague_statistics: list[str],
    hard_facts: list[str],
    *,
    section_content: SectionContent | None,
) -> None:
    scope: Literal["chapter", "section"] = "section" if section_content is not None else "chapter"
    section_id = section_content.section_id if section_content is not None else ""
    section_title = section_content.title if section_content is not None else ""
    section_prefix = f"{section_id} {section_title}: " if section_content is not None else ""
    if vague_statistics:
        issues.append(
            PublicationIssue(
                code="fact.unsourced_statistics",
                scope=scope,
                section_id=section_id,
                section_title=section_title,
                excerpt=vague_statistics[0],
                message=f"{section_prefix}存在疑似无明确来源的统计或趋势断言: {'；'.join(vague_statistics[:3])}",
                suggestion="补充具体来源，或改写为非统计化、低风险表述。",
            )
        )
    if hard_facts:
        issues.append(
            PublicationIssue(
                code="fact.unsourced_hard_fact",
                scope=scope,
                section_id=section_id,
                section_title=section_title,
                excerpt=hard_facts[0],
                message=f"{section_prefix}存在疑似无明确来源的精确硬事实: {'；'.join(hard_facts[:3])}",
                suggestion="为年份、版本、时延、吞吐、金额等精确断言补充 [S]/[W] 证据，或改写为定性/假设场景。",
            )
        )
