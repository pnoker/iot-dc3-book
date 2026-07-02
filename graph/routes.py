"""
状态图路由函数
"""

from __future__ import annotations

from typing import Any, Literal

from core.state import BookState


def _as_state(state: BookState | dict[str, Any]) -> BookState:
    return BookState(**state) if isinstance(state, dict) else state


def route_after_plan_review(state: BookState | dict[str, Any]) -> Literal["approved", "revise_plan"]:
    """大纲审后路由"""
    return "approved"


def route_after_style_check(state: BookState | dict[str, Any]) -> Literal["pass", "fail"]:
    s = _as_state(state)
    chapter = s.get_current_chapter()
    content = s.get_chapter_content(chapter.id) if chapter else None
    if content and content.style_feedback:
        return "fail"
    return "pass"


def route_after_fact_check(state: BookState | dict[str, Any]) -> Literal["pass", "fail"]:
    s = _as_state(state)
    chapter = s.get_current_chapter()
    content = s.get_chapter_content(chapter.id) if chapter else None
    if content and content.fact_feedback:
        return "fail"
    return "pass"


def route_after_editor_review(state: BookState | dict[str, Any]) -> Literal["pass", "fail"]:
    s = _as_state(state)
    return "fail" if s.needs_revision else "pass"


def route_after_revise(state: BookState | dict[str, Any]) -> Literal["revise", "advance"]:
    """修订后路由：未达上限继续修改，达上限则止损放行推进下一章。"""
    s = _as_state(state)
    return "revise" if s.needs_revision else "advance"


def route_next_chapter(state: BookState | dict[str, Any]) -> Literal["next", "done"]:
    s = _as_state(state)
    return "done" if s.current_phase == "final_review" else "next"
