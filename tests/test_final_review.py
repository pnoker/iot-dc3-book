from __future__ import annotations

from core.state import BookState, ChapterContent, ChapterPlan, PartPlan
from graph.node_final import node_final_review, node_final_revise
from graph.routes import route_after_final_review


class _DirectorNeedsRevision:
    def final_review(self, state: BookState) -> dict:
        return {
            "pass": False,
            "overall_score": 6,
            "revise_chapters": [{"chapter_id": 1, "reason": "术语与全书不一致"}],
            "suggestions": ["统一术语"],
            "summary": "需返修",
        }


class _DirectorClean:
    def final_review(self, state: BookState) -> dict:
        return {"pass": True, "overall_score": 9, "revise_chapters": [], "suggestions": [], "summary": "优秀"}


class _Writer:
    def revise(self, state: BookState, feedback: str) -> str:
        return "# 终审修订正文\n\n已按终审反馈修订全书级问题。"


def _state(round_: int = 0, max_round: int = 1) -> BookState:
    state = BookState(
        parts=[PartPlan(name="基础篇", prefix="一", chapters=[ChapterPlan(id=1, title="概述", summary="")])],
        final_revision_round=round_,
        max_final_revision_round=max_round,
    )
    state.chapters.append(ChapterContent(chapter_id=1, title="概述", markdown="# 原正文"))
    return state


def test_final_review_flags_chapters_for_revision_within_limit() -> None:
    state = _state(round_=0)

    update = node_final_review(state, _DirectorNeedsRevision())
    updated = BookState(**{**state.model_dump(), **update})

    assert updated.final_revision_chapters == [1]
    assert updated.get_chapter_content(1).review_feedback  # 终审反馈已写入
    assert route_after_final_review(updated) == "revise"


def test_final_review_releases_when_round_limit_reached() -> None:
    # 已达返修轮次上限 → 即使 Director 要求返修也止损放行输出
    state = _state(round_=1, max_round=1)

    update = node_final_review(state, _DirectorNeedsRevision())
    updated = BookState(**{**state.model_dump(), **update})

    assert updated.final_revision_chapters == []
    assert updated.current_phase == "completed"
    assert route_after_final_review(updated) == "output"


def test_final_review_clean_goes_straight_to_output() -> None:
    state = _state()

    update = node_final_review(state, _DirectorClean())
    updated = BookState(**{**state.model_dump(), **update})

    assert updated.final_revision_chapters == []
    assert route_after_final_review(updated) == "output"


def test_final_revise_rewrites_flagged_chapters_and_bumps_round() -> None:
    state = _state(round_=0)
    content = state.get_chapter_content(1)
    content.review_feedback = '{"source": "final_review", "reason": "术语不一致"}'
    state.upsert_chapter_content(content)
    state.final_revision_chapters = [1]

    update = node_final_revise(state, _Writer())
    updated = BookState(**{**state.model_dump(), **update})

    assert "终审修订正文" in updated.get_chapter_content(1).markdown
    assert updated.final_revision_chapters == []
    assert updated.final_revision_round == 1
    assert updated.get_chapter_content(1).review_feedback == ""
