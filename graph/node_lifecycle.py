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
    books_dir = paths.books_dir
    index_path = str(paths.rag_manifest)
    count = rag.index_books(str(books_dir), index_path)
    logger.info("📚 [索引] 完成，共 %d 个分块", count)
    return {"current_phase": "planning"}


def node_planning(state: BookState | dict[str, Any], planner: Any) -> dict[str, Any]:
    """大纲规划"""
    logger.info("📝 [规划] 生成大纲和伏笔规划...")
    s = BookState(**state) if isinstance(state, dict) else state
    parts, foreshadows = planner.plan(s)
    if not parts:
        logger.warning("Planner 未返回可匹配篇章，保留配置中的原始篇章，避免生成空书。")
        parts = s.parts
    return {
        "parts": [p.model_dump() for p in parts],
        "foreshadows": [f.model_dump() for f in foreshadows],
        "current_phase": "plan_review",
    }


def node_plan_review(state: BookState | dict[str, Any]) -> dict[str, Any]:
    """大纲审阅（human-in-the-loop 节点）"""
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
    return {"current_phase": "writing"}


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
