from __future__ import annotations

from core.state import BookState, ChapterContent, ChapterPlan, ForeshadowItem, PartPlan
from graph.node_quality import node_editor_review, node_quality_gate, node_style_check
from graph.routes import route_after_quality_gate


class _PassingEditor:
    def __init__(self, checks: list[dict] | None = None) -> None:
        self._checks = checks or []

    def review(self, state: BookState) -> dict:
        return {"pass": True, "overall_score": 8, "foreshadow_checks": self._checks, "issues": []}


class _FailingEditor:
    def review(self, state: BookState) -> dict:
        return {"pass": False, "overall_score": 4, "foreshadow_checks": [], "issues": [{"severity": "critical"}]}


class _PassingStyleGuard:
    def check(self, state: BookState) -> dict:
        return {"pass": True, "score": 9, "issues": [], "statistics": {}}


def _state(content: ChapterContent, foreshadows: list[ForeshadowItem] | None = None) -> BookState:
    state = BookState(
        parts=[PartPlan(name="基础篇", prefix="一", chapters=[ChapterPlan(id=1, title="概述", summary="")])],
        max_revision_count=2,
    )
    state.chapters.append(content)
    state.foreshadows = foreshadows or []
    return state


def test_quality_gate_fails_when_any_feedback_present() -> None:
    # 三门中事实门留有 feedback → 汇总判定为需返修
    state = _state(ChapterContent(chapter_id=1, title="概述", markdown="# 正文", fact_feedback='{"pass": false}'))

    update = node_quality_gate(state)
    updated = BookState(**{**state.model_dump(), **update})

    assert updated.needs_revision is True
    assert updated.revision_target_chapter == 1
    assert route_after_quality_gate(updated) == "fail"


def test_quality_gate_passes_when_all_clear_and_marks_reviewed() -> None:
    state = _state(ChapterContent(chapter_id=1, title="概述", markdown="# 正文"))

    update = node_quality_gate(state)
    updated = BookState(**{**state.model_dump(), **update})

    assert updated.needs_revision is False
    assert updated.get_current_chapter().status == "reviewed"
    assert route_after_quality_gate(updated) == "pass"


def test_editor_review_stores_foreshadow_checks_on_pass() -> None:
    checks = [{"id": "F001", "type": "resolve", "done": True}]
    state = _state(ChapterContent(chapter_id=1, title="概述", markdown="# 正文"))

    update = node_editor_review(state, _PassingEditor(checks))
    updated = BookState(**{**state.model_dump(), **update})

    assert updated.get_chapter_content(1).foreshadow_checks == checks
    assert updated.get_chapter_content(1).review_feedback == ""


def test_quality_gate_resolves_foreshadow_only_when_editor_confirms_done() -> None:
    # F001 计划第 1 章回收，Editor 核验 done=True → gate 通过时标 resolved
    fs = ForeshadowItem(id="F001", description="呼应", planted_chapter=0, planned_resolve_chapter=1)
    content = ChapterContent(chapter_id=1, title="概述", markdown="# 正文")
    content.foreshadow_checks = [{"id": "F001", "type": "resolve", "done": True}]
    state = _state(content, [fs])

    update = node_quality_gate(state)
    updated = BookState(**{**state.model_dump(), **update})

    assert updated.foreshadows[0].status == "resolved"


def test_quality_gate_does_not_resolve_foreshadow_when_not_done() -> None:
    # Editor 核验 done=False → 不得机械标 resolved（修复「回收不存在的伏笔」）
    fs = ForeshadowItem(id="F001", description="呼应", planted_chapter=0, planned_resolve_chapter=1)
    content = ChapterContent(chapter_id=1, title="概述", markdown="# 正文")
    content.foreshadow_checks = [{"id": "F001", "type": "resolve", "done": False}]
    state = _state(content, [fs])

    update = node_quality_gate(state)
    updated = BookState(**{**state.model_dump(), **update})

    assert updated.foreshadows[0].status == "planted"  # 仍未回收


def test_editor_review_fail_clears_foreshadow_checks() -> None:
    # F 修复：fail 分支不遗留伏笔核验（也不会在 gate 里被误用）
    content = ChapterContent(chapter_id=1, title="概述", markdown="# 正文")
    content.foreshadow_checks = [{"id": "F001", "type": "resolve", "done": True}]
    state = _state(content)

    update = node_editor_review(state, _FailingEditor())
    updated = BookState(**{**state.model_dump(), **update})

    assert updated.get_chapter_content(1).foreshadow_checks == []
    assert updated.get_chapter_content(1).review_feedback


def test_style_check_is_pure_evaluation() -> None:
    state = _state(ChapterContent(chapter_id=1, title="概述", markdown="# 正文", style_feedback='{"pass": false}'))

    update = node_style_check(state, _PassingStyleGuard())
    updated = BookState(**{**state.model_dump(), **update})

    assert updated.get_chapter_content(1).style_feedback == ""
    assert updated.needs_revision is False  # 纯评审不路由
