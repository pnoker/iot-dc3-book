from __future__ import annotations

import pytest

from core.quality_rules import ensure_book_releasable, evaluate_chapter_quality
from core.state import BookState, ChapterContent, ChapterPlan, PartPlan, QualitySettings
from core.state_validation import is_complete_book_state, require_complete_book_state


def _state(content: ChapterContent | None = None) -> BookState:
    state = BookState(
        parts=[PartPlan(name="基础篇", prefix="一", chapters=[ChapterPlan(id=1, title="概述")])],
        quality=QualitySettings(
            enabled=True,
            mode="release",
            min_words_per_chapter=100,
            target_words_per_chapter=150,
            min_heading_count=3,
            min_figures_or_tables=1,
            require_summary=True,
            require_exercises=True,
            min_exercise_count=3,
            require_existing_local_images=True,
            forbid_placeholder_images=True,
            forbid_unsourced_statistics=True,
            forbid_unresolved_final_review=True,
        ),
    )
    if content is not None:
        state.chapters.append(content)
    return state


def test_publication_quality_fails_short_chapter_and_missing_assets() -> None:
    content = ChapterContent(chapter_id=1, title="概述", markdown="# 第1章 概述\n\n据行业调查，超过六成项目延期。")
    report = evaluate_chapter_quality(_state(content), content)

    assert report.pass_ is False
    codes = {issue.code for issue in report.issues}
    assert "word_count.too_short" in codes
    assert "asset.missing_figure_or_table" in codes
    assert "fact.unsourced_statistics" in codes


def test_publication_quality_fails_when_chapter_exceeds_target_limit() -> None:
    content = ChapterContent(
        chapter_id=1,
        title="概述",
        markdown="# 第1章 概述\n\n" + "内容" * 100,
    )
    state = _state(content)
    state.writing.default_chapter_target_words = 150
    state.quality.max_words_over_target_ratio = 1.2

    report = evaluate_chapter_quality(state, content)

    codes = {issue.code for issue in report.issues}
    assert "word_count.too_long" in codes


def test_publication_quality_flags_unsourced_precise_hard_facts() -> None:
    content = ChapterContent(
        chapter_id=1,
        title="概述",
        markdown="# 第1章 概述\n\n2023年，某城市平台将端到端时延稳定控制在50ms，相关市场规模达到100亿元。",
    )

    report = evaluate_chapter_quality(_state(content), content)

    codes = {issue.code for issue in report.issues}
    assert "fact.unsourced_hard_fact" in codes


def test_publication_quality_allows_sourced_or_hypothetical_hard_facts() -> None:
    sourced = ChapterContent(
        chapter_id=1,
        title="概述",
        markdown="# 第1章 概述\n\n2023年，相关标准进入新阶段。（资料：[S1]）",
    )
    hypothetical = ChapterContent(
        chapter_id=1,
        title="概述",
        markdown="# 第1章 概述\n\n在假设场景中，网关每10秒采集一次数据，用于说明采集周期对链路压力的影响。",
    )

    sourced_codes = {issue.code for issue in evaluate_chapter_quality(_state(sourced), sourced).issues}
    hypothetical_codes = {issue.code for issue in evaluate_chapter_quality(_state(hypothetical), hypothetical).issues}

    assert "fact.unsourced_hard_fact" not in sourced_codes
    assert "fact.unsourced_hard_fact" not in hypothetical_codes


def test_publication_quality_accepts_structured_chapter(tmp_path) -> None:
    image = tmp_path / "figure.png"
    image.write_bytes(b"png")
    markdown = f"""# 第1章 概述

## 1.1 工程问题
这是一个足够长的段落，用来解释工程背景、技术约束、系统边界、风险来源、实践方法和读者需要掌握的核心能力。这里避免无来源统计，只讨论可验证的工程判断。

![图1-1 架构图]({image})

## 本章小结
本章总结核心概念、工程判断和实践路径，帮助读者建立稳定的知识结构。

## 思考与练习
1. 解释核心概念。
2. 设计一个小型方案。
3. 分析一个工程风险。
"""
    content = ChapterContent(chapter_id=1, title="概述", markdown=markdown)
    report = evaluate_chapter_quality(_state(content), content, base_dir=tmp_path)

    assert report.pass_ is True


def test_release_state_requires_publication_approval() -> None:
    state = _state(ChapterContent(chapter_id=1, title="概述", markdown="# 正文"))
    state.current_phase = "completed"

    assert is_complete_book_state(state) is False
    with pytest.raises(RuntimeError, match="未通过出版级终审"):
        require_complete_book_state(state)
    with pytest.raises(RuntimeError, match="publication_approved"):
        ensure_book_releasable(state)


def test_release_rechecks_chapter_quality_even_when_approved() -> None:
    state = _state(ChapterContent(chapter_id=1, title="概述", markdown="# 正文"))
    state.current_phase = "completed"
    state.publication_approved = True

    with pytest.raises(RuntimeError, match="质量复检失败"):
        ensure_book_releasable(state)

