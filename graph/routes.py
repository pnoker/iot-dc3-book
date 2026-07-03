"""
状态图路由函数
"""

from __future__ import annotations

from typing import Any, Literal

from core.state import BookState


def _as_state(state: BookState | dict[str, Any]) -> BookState:
    return BookState(**state) if isinstance(state, dict) else state


def route_after_plan_review(state: BookState | dict[str, Any]) -> Literal["approved", "revise_plan"]:
    """大纲门路由：评审通过进入写作，未过且未达上限回退重规划。"""
    s = _as_state(state)
    return "revise_plan" if s.current_phase == "planning" else "approved"


def route_after_quality_gate(state: BookState | dict[str, Any]) -> Literal["pass", "fail"]:
    """质量门汇总路由：三门全通过则推进，任一未过则转修订。"""
    s = _as_state(state)
    return "fail" if s.needs_revision else "pass"


def route_after_revise(state: BookState | dict[str, Any]) -> Literal["revise", "advance"]:
    """修订后路由：未达上限继续修改，达上限则止损放行推进下一章。"""
    s = _as_state(state)
    return "revise" if s.needs_revision else "advance"


def route_next_chapter(state: BookState | dict[str, Any]) -> Literal["next", "done"]:
    s = _as_state(state)
    return "done" if s.current_phase == "final_review" else "next"


def route_after_final_review(state: BookState | dict[str, Any]) -> Literal["revise", "output"]:
    """终审门路由：有需返修章节且未达轮次上限则返修，否则定稿输出。"""
    s = _as_state(state)
    return "revise" if s.final_revision_chapters else "output"
