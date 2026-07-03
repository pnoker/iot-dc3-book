from __future__ import annotations

from typing import Any

from agents.plan_reviewer import PlanReviewerAgent
from core.state import BookState, ChapterPlan, PartPlan
from graph.node_lifecycle import node_plan_review
from graph.routes import route_after_plan_review


class _ReviewerLLM:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls = 0

    def chat_json(self, system: str, user: str, temperature: float | None = None) -> dict[str, Any]:
        self.calls += 1
        return self.response


def _candidates() -> list[dict]:
    return [
        {"parts": [{"name": "基础篇", "chapters": [{"id": 1, "outline": "方案A", "key_points": ["a"]}]}], "foreshadows": []},
        {"parts": [{"name": "基础篇", "chapters": [{"id": 1, "outline": "方案B", "key_points": ["b"]}]}], "foreshadows": []},
    ]


def _state() -> BookState:
    return BookState(
        book_title="测试书",
        parts=[PartPlan(name="基础篇", prefix="一", chapters=[ChapterPlan(id=1, title="概述", summary="")])],
        max_plan_revision_count=2,
    )


def test_plan_reviewer_selects_best_candidate() -> None:
    llm = _ReviewerLLM({"pass": True, "best_index": 1, "scores": [], "reason": "B 更优"})
    result = PlanReviewerAgent(llm).review(_state(), _candidates())

    assert result["pass"] is True
    assert result["best_index"] == 1


def test_plan_reviewer_clamps_out_of_range_best_index() -> None:
    llm = _ReviewerLLM({"pass": True, "best_index": 9, "scores": [], "reason": "越界"})
    result = PlanReviewerAgent(llm).review(_state(), _candidates())

    assert result["best_index"] == 0  # 越界回退 0


def test_plan_reviewer_empty_candidates_fails() -> None:
    result = PlanReviewerAgent(_ReviewerLLM({})).review(_state(), [])
    assert result["pass"] is False
    assert result["best_index"] == -1


def test_plan_review_routes_back_to_planning_when_review_failed() -> None:
    state = _state()
    state.plan_needs_revision = True
    state.plan_revision_count = 0

    update = node_plan_review(state)
    updated = BookState(**{**state.model_dump(), **update})

    assert update["current_phase"] == "planning"
    assert update["plan_revision_count"] == 1
    assert route_after_plan_review(updated) == "revise_plan"


def test_plan_review_accepts_when_revision_limit_reached() -> None:
    state = _state()
    state.plan_needs_revision = True
    state.plan_revision_count = 2  # 已达上限

    update = node_plan_review(state)
    updated = BookState(**{**state.model_dump(), **update})

    assert update["current_phase"] == "writing"
    assert route_after_plan_review(updated) == "approved"


def test_plan_review_approves_when_review_passed() -> None:
    state = _state()
    state.plan_needs_revision = False

    update = node_plan_review(state)
    updated = BookState(**{**state.model_dump(), **update})

    assert update["current_phase"] == "writing"
    assert route_after_plan_review(updated) == "approved"
