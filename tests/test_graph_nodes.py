from __future__ import annotations

import pytest

from agents.planner import PlannerAgent
from core.state import BookState, ChapterContent, ChapterPlan, ForeshadowItem, PartPlan
from core.state_validation import is_complete_book_state, require_complete_book_state
from graph.node_chapter import node_write
from graph.node_lifecycle import node_plan_review, node_planning
from graph.node_quality import node_fact_check, node_revise, node_style_check


class _PassingStyleGuard:
    def check(self, state: BookState) -> dict:
        return {"pass": True, "score": 9, "issues": [], "statistics": {}}


class _PassingFactChecker:
    def check(self, state: BookState) -> dict:
        return {"pass": True, "score": 9, "claims": [], "issues": []}


class _FailingFactChecker:
    def check(self, state: BookState) -> dict:
        return {"pass": False, "score": 4, "issues": [{"description": "缺少事实依据"}]}


class _Writer:
    def write(self, state: BookState) -> str:
        return "# 新正文\n\n新内容"

    def revise(self, state: BookState, feedback: str) -> str:
        return "# 修订正文\n\n已根据反馈修订"


class _EmptyPlanner:
    def plan(self, state: BookState) -> tuple[list[PartPlan], list[object]]:
        return [], []


class _PlannerLLM:
    def chat_json(self, *args: object, **kwargs: object) -> dict[str, object]:
        return {
            "parts": [
                {
                    "name": "基础篇",
                    "chapters": [
                        {"id": 1, "outline": "一.1 总览", "key_points": ["连接", "智能"]},
                    ],
                }
            ],
            "foreshadows": [
                {"id": "F001", "description": "后文展开 AIoT", "planted_chapter": 1, "planned_resolve_chapter": 7}
            ],
        }


def _state_with_chapter(content: ChapterContent | None = None) -> BookState:
    state = BookState(
        parts=[
            PartPlan(
                name="基础篇",
                prefix="一",
                chapters=[ChapterPlan(id=1, title="物联网概述", summary="概述")],
            )
        ],
        max_revision_count=2,
    )
    if content:
        state.chapters.append(content)
    return state


def test_style_check_pass_clears_stale_feedback() -> None:
    state = _state_with_chapter(
        ChapterContent(
            chapter_id=1,
            title="物联网概述",
            markdown="# 正文",
            style_feedback='{"pass": false}',
        )
    )

    update = node_style_check(state, _PassingStyleGuard())
    updated = BookState(**{**state.model_dump(), **update})

    assert updated.get_chapter_content(1).style_feedback == ""


def test_fact_check_failure_records_feedback_for_revision() -> None:
    state = _state_with_chapter(ChapterContent(chapter_id=1, title="物联网概述", markdown="# 正文"))

    update = node_fact_check(state, _FailingFactChecker())
    updated = BookState(**{**state.model_dump(), **update})

    assert updated.get_chapter_content(1).fact_feedback
    assert updated.needs_revision is True
    assert updated.revision_target_chapter == 1


def test_fact_check_pass_clears_stale_feedback() -> None:
    state = _state_with_chapter(
        ChapterContent(chapter_id=1, title="物联网概述", markdown="# 正文", fact_feedback='{"pass": false}')
    )

    update = node_fact_check(state, _PassingFactChecker())
    updated = BookState(**{**state.model_dump(), **update})

    assert updated.get_chapter_content(1).fact_feedback == ""
    assert updated.get_current_chapter().status == "fact_checked"


def test_plan_review_marks_state_ready_for_writing() -> None:
    state = _state_with_chapter()

    update = node_plan_review(state)

    assert update["current_phase"] == "writing"


def test_planning_keeps_existing_parts_when_planner_returns_no_parts() -> None:
    state = _state_with_chapter()

    update = node_planning(state, _EmptyPlanner())
    updated = BookState(**{**state.model_dump(), **update})

    assert len(updated.parts) == 1
    assert updated.parts[0].chapters[0].title == "物联网概述"


def test_planner_matches_model_part_by_chapter_ids_when_name_differs() -> None:
    state = BookState(
        book_title="测试书",
        parts=[
            PartPlan(
                name="基础篇 · 万物互联",
                prefix="一",
                chapters=[ChapterPlan(id=1, title="物联网概述", summary="概述")],
            )
        ],
    )
    planner = PlannerAgent(_PlannerLLM())

    parts, foreshadows = planner.plan(state)

    assert len(parts) == 1
    assert parts[0].name == "基础篇 · 万物互联"
    assert parts[0].chapters[0].outline == "一.1 总览"
    assert parts[0].chapters[0].key_points == ["连接", "智能"]
    assert foreshadows == [
        ForeshadowItem(id="F001", description="后文展开 AIoT", planted_chapter=1, planned_resolve_chapter=7)
    ]


def test_completed_state_without_chapters_is_not_valid_complete_book() -> None:
    state = _state_with_chapter()
    state.current_phase = "completed"

    assert is_complete_book_state(state) is False
    with pytest.raises(RuntimeError, match="已写章节 0/1"):
        require_complete_book_state(state)


def test_completed_state_with_all_chapters_written_is_valid_complete_book() -> None:
    state = _state_with_chapter(ChapterContent(chapter_id=1, title="物联网概述", markdown="# 正文"))
    state.current_phase = "completed"

    assert is_complete_book_state(state) is True


def test_write_updates_existing_chapter_instead_of_appending_duplicate() -> None:
    state = _state_with_chapter(
        ChapterContent(chapter_id=1, title="物联网概述", markdown="# 旧正文", word_count=5)
    )

    update = node_write(state, _Writer())
    updated = BookState(**{**state.model_dump(), **update})

    assert len(updated.chapters) == 1
    assert updated.get_chapter_content(1).markdown == "# 新正文\n\n新内容"


def test_revise_stops_when_revision_limit_reached() -> None:
    state = _state_with_chapter(
        ChapterContent(
            chapter_id=1,
            title="物联网概述",
            markdown="# 正文",
            revision_count=2,
        )
    )

    with pytest.raises(RuntimeError, match="修订次数已达上限"):
        node_revise(state)
