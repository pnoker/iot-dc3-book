"""出版级确定性质量门。"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from core.markdown_assets import count_figures_or_tables, count_headings, find_placeholder_images, missing_local_images
from core.state import BookState, ChapterContent, QualitySettings
from core.wordcount import count_words

if TYPE_CHECKING:
    from pathlib import Path


class PublicationIssue(BaseModel):
    """确定性质量门问题。"""

    code: str
    severity: str = "major"
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
                "issues": [issue.model_dump() for issue in self.issues],
                "statistics": self.statistics,
            },
            ensure_ascii=False,
        )


_SUMMARY_RE = re.compile(r"(^|\n)##\s*(本章小结|小结|章节小结)\s*$", re.MULTILINE)
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
    actual_words = count_words(markdown)
    target_words = max(settings.target_words_per_chapter, state.writing.target_for_chapter(content.chapter_id))
    max_words = int(target_words * settings.max_words_over_target_ratio) if settings.max_words_over_target_ratio else 0
    heading_count = count_headings(markdown)
    figure_or_table_count = count_figures_or_tables(markdown)
    issues: list[PublicationIssue] = []

    _check_word_count(settings, actual_words, target_words, max_words, issues)
    _check_structure(settings, markdown, heading_count, figure_or_table_count, issues)
    _check_assets(settings, markdown, base_dir, issues)
    _check_unsourced_hard_facts(settings, markdown, issues)

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
    if settings.require_summary and not _SUMMARY_RE.search(markdown):
        issues.append(
            PublicationIssue(
                code="structure.missing_summary",
                message="缺少“本章小结”章节。",
                suggestion="增加本章核心观点、工程判断和读者应掌握能力的回顾。",
            )
        )
    if settings.require_exercises:
        exercise_match = _EXERCISE_RE.search(markdown)
        exercise_count = len(_EXERCISE_ITEM_RE.findall(markdown[exercise_match.start():])) if exercise_match else 0
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


def _check_unsourced_hard_facts(settings: QualitySettings, markdown: str, issues: list[PublicationIssue]) -> None:
    if not settings.forbid_unsourced_statistics:
        return
    vague_statistics: list[str] = []
    hard_facts: list[str] = []
    for paragraph in re.split(r"\n\s*\n", markdown):
        text = paragraph.strip().replace("\n", " ")
        if not text or text.startswith("|") or text.startswith("#") or _SOURCE_HINT_RE.search(text):
            continue
        if _VAGUE_STAT_RE.search(text):
            vague_statistics.append(text[:120])
            continue
        if _HARD_FACT_RE.search(text) and not _HYPOTHETICAL_HINT_RE.search(text):
            hard_facts.append(text[:120])
    if vague_statistics:
        issues.append(
            PublicationIssue(
                code="fact.unsourced_statistics",
                message=f"存在疑似无明确来源的统计或趋势断言: {'；'.join(vague_statistics[:3])}",
                suggestion="补充具体来源，或改写为非统计化、低风险表述。",
            )
        )
    if hard_facts:
        issues.append(
            PublicationIssue(
                code="fact.unsourced_hard_fact",
                message=f"存在疑似无明确来源的精确硬事实: {'；'.join(hard_facts[:3])}",
                suggestion="为年份、版本、时延、吞吐、金额等精确断言补充 [S]/[W] 证据，或改写为定性/假设场景。",
            )
        )
