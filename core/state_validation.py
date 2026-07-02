"""BookState 完整性校验。"""

from __future__ import annotations

from core.state import BookState


class IncompleteBookStateError(RuntimeError):
    """书稿 checkpoint 不完整。"""


def is_complete_book_state(state: BookState) -> bool:
    """判断 checkpoint 是否代表一本真正完成的书。"""
    expected_chapter_ids = {chapter.id for chapter in state.get_all_chapters_flat()}
    written_chapter_ids = {chapter.chapter_id for chapter in state.chapters if chapter.markdown.strip()}
    return state.current_phase == "completed" and bool(expected_chapter_ids) and expected_chapter_ids <= written_chapter_ids


def require_complete_book_state(state: BookState) -> None:
    """要求状态已经完成全部章节，否则阻止误输出空书。"""
    if is_complete_book_state(state):
        return
    expected = len(state.get_all_chapters_flat())
    written = len({chapter.chapter_id for chapter in state.chapters if chapter.markdown.strip()})
    raise IncompleteBookStateError(
        f"书稿未完整生成：已写章节 {written}/{expected}，请使用 run --fresh 或 reset --yes 后重新执行。"
    )
