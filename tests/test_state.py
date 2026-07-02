"""core.state 单元测试"""

from core.state import BookState, ChapterContent, ChapterPlan, ForeshadowItem, PartPlan


def test_book_state_defaults():
    state = BookState()
    assert state.book_title == ""
    assert state.parts == []
    assert state.current_phase == "init"


def test_advance_to_next_chapter():
    state = BookState(
        parts=[
            PartPlan(
                name="基础篇",
                prefix="一",
                chapters=[
                    ChapterPlan(id=1, title="Ch1"),
                    ChapterPlan(id=2, title="Ch2"),
                ],
            ),
            PartPlan(
                name="技术篇",
                prefix="二",
                chapters=[
                    ChapterPlan(id=3, title="Ch3"),
                ],
            ),
        ]
    )
    assert state.get_current_chapter().id == 1
    assert state.advance_to_next_chapter() is True
    assert state.get_current_chapter().id == 2
    assert state.advance_to_next_chapter() is True
    assert state.get_current_chapter().id == 3
    assert state.advance_to_next_chapter() is False


def test_foreshadow_filtering():
    state = BookState(
        foreshadows=[
            ForeshadowItem(id="F1", description="test", planted_chapter=1, planned_resolve_chapter=5, status="planted"),
            ForeshadowItem(
                id="F2", description="test", planted_chapter=2, planned_resolve_chapter=6, status="resolved"
            ),
        ]
    )
    planted = state.get_planted_foreshadows()
    assert len(planted) == 1
    assert planted[0].id == "F1"


def test_upsert_chapter_content_replaces_by_chapter_id():
    state = BookState(
        chapters=[ChapterContent(chapter_id=1, title="旧标题", markdown="旧内容", word_count=3)]
    )

    state.upsert_chapter_content(ChapterContent(chapter_id=1, title="新标题", markdown="新内容", word_count=3))

    assert len(state.chapters) == 1
    assert state.get_chapter_content(1).title == "新标题"
    assert state.get_chapter_content(1).markdown == "新内容"


def test_set_current_chapter_by_id_updates_indices():
    state = BookState(
        parts=[
            PartPlan(name="上篇", prefix="一", chapters=[ChapterPlan(id=1, title="第一章")]),
            PartPlan(
                name="下篇",
                prefix="二",
                chapters=[ChapterPlan(id=2, title="第二章"), ChapterPlan(id=3, title="第三章")],
            ),
        ]
    )

    assert state.set_current_chapter_by_id(3) is True
    assert state.current_part_idx == 1
    assert state.current_chapter_idx == 1
    assert state.get_current_chapter().id == 3


def test_clear_chapter_feedback_resets_revision_flags():
    state = BookState(
        needs_revision=True,
        revision_target_chapter=1,
        chapters=[
            ChapterContent(
                chapter_id=1,
                title="第一章",
                markdown="正文",
                review_feedback="审校反馈",
                style_feedback="风格反馈",
                fact_feedback="事实反馈",
            )
        ],
    )

    state.clear_chapter_feedback(1)

    content = state.get_chapter_content(1)
    assert content.review_feedback == ""
    assert content.style_feedback == ""
    assert content.fact_feedback == ""
    assert state.needs_revision is False
    assert state.revision_target_chapter == 0
