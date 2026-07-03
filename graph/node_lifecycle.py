"""
生命周期节点：初始化、索引、规划、推进章节
"""

from __future__ import annotations

from typing import Any

from core.config import config_to_book_state, get_config_paths
from core.config_models import AppConfig
from core.log import get_logger
from core.state import BookState

logger = get_logger("nodes")


def node_init(state: BookState | dict[str, Any], cfg: AppConfig) -> dict[str, Any]:
    """初始化：加载配置，构建 BookState"""
    logger.info("📋 [初始化] 加载书籍配置...")
    book_state = config_to_book_state(cfg)
    book_state.current_phase = "indexing"
    return book_state.model_dump()


def node_indexing(state: BookState | dict[str, Any], cfg: AppConfig, rag: Any) -> dict[str, Any]:
    """索引参考书籍"""
    logger.info("📚 [索引] 开始索引参考书籍...")

    paths = get_config_paths(cfg)
    index_path = str(paths.rag_manifest)
    count = rag.index_books(paths.reference_sources, index_path)
    logger.info("📚 [索引] 完成，共 %d 个分块", count)
    return {"current_phase": "planning"}


def node_planning(state: BookState | dict[str, Any], planner: Any, plan_reviewer: Any) -> dict[str, Any]:
    """大纲规划：生成多个候选，由评审择优落地。"""
    logger.info("📝 [规划] 生成候选大纲和伏笔规划...")
    s = BookState(**state) if isinstance(state, dict) else state

    candidates = planner.plan_candidates(s, n=2)
    if not candidates:
        logger.warning("Planner 未返回候选，保留配置中的原始篇章，避免生成空书。")
        return {"current_phase": "plan_review", "plan_needs_revision": False}

    review = plan_reviewer.review(s, candidates)
    best_index = review.get("best_index", 0)
    logger.info("📝 [评审] 择优候选 %d，pass=%s，理由: %s", best_index, review.get("pass"), review.get("reason", ""))

    parts, foreshadows = planner.build_plan(s, candidates[best_index])
    if not parts:
        logger.warning("最优候选未匹配到篇章，保留原始篇章。")
        parts = s.parts

    return {
        "parts": [p.model_dump() for p in parts],
        "foreshadows": [f.model_dump() for f in foreshadows],
        "current_phase": "plan_review",
        "plan_needs_revision": not review.get("pass", True),
    }


def node_plan_review(state: BookState | dict[str, Any]) -> dict[str, Any]:
    """大纲质量门：评审通过进入写作；不通过且未达上限则计数并回退重规划。"""
    s = BookState(**state) if isinstance(state, dict) else state
    logger.info("=" * 60)
    logger.info("📖 大纲预览")
    logger.info("=" * 60)
    for part in s.parts:
        logger.info("【%s】", part.name)
        for ch in part.chapters:
            logger.info("  第%d章 %s", ch.id, ch.title)
            if ch.outline:
                logger.info("    %s...", ch.outline[:200].replace("\n", "\n    "))
    logger.info("📌 伏笔规划: %d 个", len(s.foreshadows))
    for fs in s.foreshadows:
        logger.info("  - %s: %s (第%d章→第%d章)", fs.id, fs.description, fs.planted_chapter, fs.planned_resolve_chapter)
    logger.info("=" * 60)

    if s.plan_needs_revision and s.plan_revision_count < s.max_plan_revision_count:
        logger.warning("⚠️ [大纲门] 评审未通过，第 %d 次重规划...", s.plan_revision_count + 1)
        return {"current_phase": "planning", "plan_revision_count": s.plan_revision_count + 1}
    if s.plan_needs_revision:
        logger.warning("⚠️ [大纲门] 重规划已达上限 %d，接受当前大纲继续写作。", s.max_plan_revision_count)
    return {"current_phase": "writing", "plan_needs_revision": False}


def node_advance_chapter(state: BookState | dict[str, Any]) -> dict[str, Any]:
    """推进到下一章"""
    s = BookState(**state) if isinstance(state, dict) else state
    has_next = s.advance_to_next_chapter()
    if has_next:
        chapter = s.get_current_chapter()
        if chapter is None:
            return {"current_phase": "final_review"}
        logger.info("➡️ [推进] 进入第%d章 %s", chapter.id, chapter.title)
        return {
            "current_part_idx": s.current_part_idx,
            "current_chapter_idx": s.current_chapter_idx,
            "current_phase": "writing",
        }
    logger.info("✅ [完成] 所有章节写作完成！")
    return {"current_phase": "final_review"}
