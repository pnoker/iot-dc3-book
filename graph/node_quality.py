"""
质量门节点：事实核查、风格校验、审校与修订控制
"""

from __future__ import annotations

import json
from typing import Any

from core.log import get_logger
from core.state import BookState

logger = get_logger("nodes")


def node_style_check(state: BookState | dict[str, Any], style_guard: Any) -> dict[str, Any]:
    """风格校验"""
    s = BookState(**state) if isinstance(state, dict) else state
    chapter = s.get_current_chapter()
    if not chapter:
        return {}
    logger.info("🎨 [风格] 校验第%d章风格...", chapter.id)
    result = style_guard.check(s)
    content = s.get_chapter_content(chapter.id)
    if not result.get("pass", True) and content:
        content.style_feedback = json.dumps(result, ensure_ascii=False)
        s.upsert_chapter_content(content)
        return {"chapters": [c.model_dump() for c in s.chapters]}
    if content:
        content.style_feedback = ""
        s.upsert_chapter_content(content)
        s.mark_chapter_status(chapter.id, "styled")
        return {"chapters": [c.model_dump() for c in s.chapters], "parts": [p.model_dump() for p in s.parts]}
    return {}


def node_fact_check(state: BookState | dict[str, Any], fact_checker: Any) -> dict[str, Any]:
    """事实核查"""
    s = BookState(**state) if isinstance(state, dict) else state
    chapter = s.get_current_chapter()
    if not chapter:
        return {}
    logger.info("🔎 [事实] 核查第%d章事实准确性...", chapter.id)
    result = fact_checker.check(s)
    content = s.get_chapter_content(chapter.id)
    if not result.get("pass", True) and content:
        content.fact_feedback = json.dumps(result, ensure_ascii=False)
        s.upsert_chapter_content(content)
        return {
            "chapters": [c.model_dump() for c in s.chapters],
            "needs_revision": True,
            "revision_target_chapter": chapter.id,
        }
    if content:
        content.fact_feedback = ""
        s.upsert_chapter_content(content)
        s.mark_chapter_status(chapter.id, "fact_checked")
        return {
            "chapters": [c.model_dump() for c in s.chapters],
            "parts": [p.model_dump() for p in s.parts],
            "needs_revision": False,
            "revision_target_chapter": 0,
        }
    return {}


def node_editor_review(state: BookState | dict[str, Any], editor: Any) -> dict[str, Any]:
    """一致性审校"""
    s = BookState(**state) if isinstance(state, dict) else state
    chapter = s.get_current_chapter()
    if not chapter:
        return {}
    logger.info("📋 [审校] 审校第%d章...", chapter.id)
    result = editor.review(s)
    if not result.get("pass", True):
        content = s.get_chapter_content(chapter.id)
        if content:
            content.review_feedback = json.dumps(result, ensure_ascii=False)
            return {
                "chapters": [c.model_dump() for c in s.chapters],
                "needs_revision": True,
                "revision_target_chapter": chapter.id,
            }
    else:
        chapter_list = s.get_all_chapters_flat()
        for ch in chapter_list:
            if ch.id == chapter.id:
                ch.status = "reviewed"
        for fs in s.foreshadows:
            if fs.planted_chapter == chapter.id:
                fs.status = "planted"
            if fs.planned_resolve_chapter == chapter.id:
                fs.status = "resolved"
        return {
            "parts": [p.model_dump() for p in s.parts],
            "foreshadows": [f.model_dump() for f in s.foreshadows],
        }
    return {}


def node_revise(state: BookState | dict[str, Any]) -> dict[str, Any]:
    """标记需要修改"""
    s = BookState(**state) if isinstance(state, dict) else state
    chapter = s.get_current_chapter()
    if not chapter:
        return {"needs_revision": True}
    content = s.get_chapter_content(chapter.id)
    if content and content.revision_count >= s.max_revision_count:
        raise RuntimeError(f"第{chapter.id}章修订次数已达上限: {s.max_revision_count}")
    return {"needs_revision": True, "revision_target_chapter": chapter.id}
