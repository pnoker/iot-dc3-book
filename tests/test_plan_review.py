from __future__ import annotations

from typing import Any

import pytest

from agents.plan_reviewer import PlanReviewerAgent
from core.state import BookState, ChapterPlan, PartPlan


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


def test_plan_reviewer_rejects_out_of_range_best_index() -> None:
    llm = _ReviewerLLM({"pass": True, "best_index": 9, "scores": [], "reason": "越界"})

    with pytest.raises(RuntimeError, match="best_index 无效"):
        PlanReviewerAgent(llm).review(_state(), _candidates())


def test_plan_reviewer_empty_candidates_fails() -> None:
    with pytest.raises(RuntimeError, match="未生成候选大纲"):
        PlanReviewerAgent(_ReviewerLLM({})).review(_state(), [])

