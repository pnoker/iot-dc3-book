"""
章节生产节点：资料检索、写作与修订
"""

from __future__ import annotations

from typing import Any

from core.log import get_logger
from core.state import BookState, ChapterContent
from core.wordcount import count_words

logger = get_logger("nodes")


def node_research(state: BookState | dict[str, Any], researcher: Any) -> dict[str, Any]:
    """检索参考资料"""
    s = BookState(**state) if isinstance(state, dict) else state
    chunks = researcher.search(s)
    return {"reference_chunks": [c.model_dump() for c in chunks]}


def node_write(state: BookState | dict[str, Any], writer: Any) -> dict[str, Any]:
    """写作/修改"""
    s = BookState(**state) if isinstance(state, dict) else state
    chapter = s.get_current_chapter()
    if not chapter:
        return {}

    content = s.get_chapter_content(chapter.id)
    if content and s.needs_revision:
        logger.info("✏️ [修改] 修改第%d章...", chapter.id)
        feedback = "\n".join(
            feedback_part
            for feedback_part in [content.fact_feedback, content.review_feedback, content.style_feedback]
            if feedback_part
        )
        markdown = writer.revise(s, feedback)
        content.markdown = markdown
        content.word_count = count_words(markdown)
        content.revision_count += 1
        content.review_feedback = ""
        content.style_feedback = ""
        content.fact_feedback = ""
        s.upsert_chapter_content(content)
        s.clear_chapter_feedback(chapter.id)
        s.mark_chapter_status(chapter.id, "written")
        return {
            "chapters": [c.model_dump() for c in s.chapters],
            "parts": [p.model_dump() for p in s.parts],
            "needs_revision": False,
            "revision_target_chapter": 0,
        }

    logger.info("✍️ [写作] 撰写第%d章 %s...", chapter.id, chapter.title)
    markdown = writer.write(s)
    new_chapter = ChapterContent(
        chapter_id=chapter.id, title=chapter.title, markdown=markdown, word_count=count_words(markdown)
    )
    s.upsert_chapter_content(new_chapter)
    s.mark_chapter_status(chapter.id, "written")
    return {"chapters": [c.model_dump() for c in s.chapters], "parts": [p.model_dump() for p in s.parts]}
