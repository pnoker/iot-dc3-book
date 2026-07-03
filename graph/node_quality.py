"""
质量门节点：事实核查、风格校验、审校三门先各自评审打标，
再由 quality_gate 汇总统一判定，避免三门串行各自触发整章重写的拉锯。
"""

from __future__ import annotations

import json
from typing import Any

from core.log import get_logger
from core.state import BookState

logger = get_logger("nodes")


def _as_state(state: BookState | dict[str, Any]) -> BookState:
    return BookState(**state) if isinstance(state, dict) else state


def node_fact_check(state: BookState | dict[str, Any], fact_checker: Any) -> dict[str, Any]:
    """事实核查（纯评审：仅记录 fact_feedback，不路由、不改伏笔）。"""
    s = _as_state(state)
    chapter = s.get_current_chapter()
    if not chapter:
        return {}
    logger.info("🔎 [事实] 核查第%d章事实准确性...", chapter.id)
    result = fact_checker.check(s)
    content = s.get_chapter_content(chapter.id)
    if not content:
        return {}
    content.fact_feedback = "" if result.get("pass", True) else json.dumps(result, ensure_ascii=False)
    s.upsert_chapter_content(content)
    return {"chapters": [c.model_dump() for c in s.chapters]}


def node_style_check(state: BookState | dict[str, Any], style_guard: Any) -> dict[str, Any]:
    """风格校验（纯评审：仅记录 style_feedback）。"""
    s = _as_state(state)
    chapter = s.get_current_chapter()
    if not chapter:
        return {}
    logger.info("🎨 [风格] 校验第%d章风格...", chapter.id)
    result = style_guard.check(s)
    content = s.get_chapter_content(chapter.id)
    if not content:
        return {}
    content.style_feedback = "" if result.get("pass", True) else json.dumps(result, ensure_ascii=False)
    s.upsert_chapter_content(content)
    return {"chapters": [c.model_dump() for c in s.chapters]}


def node_editor_review(state: BookState | dict[str, Any], editor: Any) -> dict[str, Any]:
    """一致性审校（纯评审：记录 review_feedback，并留存伏笔核验结论供 gate 使用）。"""
    s = _as_state(state)
    chapter = s.get_current_chapter()
    if not chapter:
        return {}
    logger.info("📋 [审校] 审校第%d章...", chapter.id)
    result = editor.review(s)
    content = s.get_chapter_content(chapter.id)
    if not content:
        return {}
    if result.get("pass", True):
        content.review_feedback = ""
        # 伏笔核验结论暂存到 content，gate 通过时据此转移伏笔状态（避免按章节号机械翻转）
        content.foreshadow_checks = _extract_foreshadow_checks(result)
    else:
        content.review_feedback = json.dumps(result, ensure_ascii=False)
        content.foreshadow_checks = []
    s.upsert_chapter_content(content)
    return {"chapters": [c.model_dump() for c in s.chapters]}


def node_quality_gate(state: BookState | dict[str, Any]) -> dict[str, Any]:
    """汇总三门评审：全通过则定稿并按实际核验转移伏笔；任一未过则标记返修。"""
    s = _as_state(state)
    chapter = s.get_current_chapter()
    content = s.get_chapter_content(chapter.id) if chapter else None
    if not chapter or not content:
        return {}

    failed = [
        name
        for name, fb in (
            ("事实", content.fact_feedback),
            ("风格", content.style_feedback),
            ("审校", content.review_feedback),
        )
        if fb
    ]
    if failed:
        logger.info("🚦 [质量门] 第%d章未通过: %s，转入修订", chapter.id, "、".join(failed))
        return {"needs_revision": True, "revision_target_chapter": chapter.id}

    # 全通过：定稿本章，依据 Editor 的伏笔核验结论转移状态
    s.mark_chapter_status(chapter.id, "reviewed")
    _apply_foreshadow_checks(s, chapter.id, content.foreshadow_checks)
    content.foreshadow_checks = []
    s.upsert_chapter_content(content)
    logger.info("🚦 [质量门] 第%d章三门通过，定稿", chapter.id)
    return {
        "chapters": [c.model_dump() for c in s.chapters],
        "parts": [p.model_dump() for p in s.parts],
        "foreshadows": [f.model_dump() for f in s.foreshadows],
        "needs_revision": False,
        "revision_target_chapter": 0,
    }


def node_revise(state: BookState | dict[str, Any]) -> dict[str, Any]:
    """标记需要修改；修订到上限时止损放行，接受当前版本并推进下一章。"""
    s = _as_state(state)
    chapter = s.get_current_chapter()
    if not chapter:
        return {"needs_revision": True}
    content = s.get_chapter_content(chapter.id)
    if content and content.revision_count >= s.max_revision_count:
        last_feedback = next(
            (fb for fb in [content.fact_feedback, content.review_feedback, content.style_feedback] if fb),
            "（无反馈记录）",
        )
        logger.warning(
            "⚠️ [放行] 第%d章修订次数已达上限 %d，强制放行并接受当前版本。最后失败原因: %s",
            chapter.id,
            s.max_revision_count,
            last_feedback,
        )
        s.mark_chapter_status(chapter.id, "approved")
        s.clear_chapter_feedback(chapter.id)
        return {
            "chapters": [c.model_dump() for c in s.chapters],
            "parts": [p.model_dump() for p in s.parts],
            "needs_revision": False,
            "revision_target_chapter": 0,
            "error_message": f"第{chapter.id}章修订到上限 {s.max_revision_count} 仍未通过，已强制放行。最后失败原因: {last_feedback}",
        }
    return {"needs_revision": True, "revision_target_chapter": chapter.id}


def _extract_foreshadow_checks(result: dict[str, Any]) -> list[dict[str, Any]]:
    """从 Editor 报告提取合法的伏笔核验条目 [{id, type, done}]。"""
    raw = result.get("foreshadow_checks")
    if not isinstance(raw, list):
        return []
    checks: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        fid = item.get("id")
        ftype = item.get("type")
        if isinstance(fid, str) and ftype in ("plant", "resolve"):
            checks.append({"id": fid, "type": ftype, "done": bool(item.get("done"))})
    return checks


def _apply_foreshadow_checks(state: BookState, chapter_id: int, checks: list[dict[str, Any]]) -> None:
    """依据 Editor 的实际核验结论转移伏笔状态，而非按章节号机械翻转。

    - resolve 且 done: 标记 resolved
    - plant 且 done: 保持 planted（已埋入，待后续回收）
    - 未达成: 不翻转状态，issues 已由 Editor 反馈驱动返修
    """
    by_id = {c["id"]: c for c in checks}
    for fs in state.foreshadows:
        check = by_id.get(fs.id)
        if not check:
            continue
        if check["type"] == "resolve" and check["done"] and fs.planned_resolve_chapter == chapter_id:
            fs.status = "resolved"
        elif check["type"] == "plant" and check["done"] and fs.planted_chapter == chapter_id:
            fs.status = "planted"
