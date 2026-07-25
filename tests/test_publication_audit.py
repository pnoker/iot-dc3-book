from __future__ import annotations

from core.publication_audit import audit_publication_readiness, summarize_publication_audit
from core.state import BookState, ChapterContent, ChapterPlan, ForeshadowItem, PartPlan, SectionContent, SectionPlan


def _state_for_audit() -> BookState:
    return BookState(
        parts=[
            PartPlan(
                name="基础篇",
                prefix="一",
                chapters=[
                    ChapterPlan(
                        id=1,
                        title="第一章",
                        status="approved",
                        sections=[
                            SectionPlan(
                                id="1.1.1",
                                chapter_id=1,
                                title="小节一",
                                heading="1.1.1 小节一",
                                parent_title="基础概念",
                                status="reviewed",
                            )
                        ],
                    ),
                    ChapterPlan(
                        id=2,
                        title="第二章",
                        status="approved",
                        sections=[
                            SectionPlan(
                                id="2.1.1",
                                chapter_id=2,
                                title="小节二",
                                heading="2.1.1 小节二",
                                parent_title="平台设计",
                                status="reviewed",
                            )
                        ],
                    ),
                ],
            )
        ],
        section_contents=[
            SectionContent(section_id="1.1.1", chapter_id=1, title="小节一", markdown="### 1.1.1 小节一\n\n正文"),
            SectionContent(section_id="2.1.1", chapter_id=2, title="小节二", markdown="### 2.1.1 小节二\n\n正文"),
        ],
        chapters=[
            ChapterContent(
                chapter_id=1,
                title="第一章",
                markdown="# 第1章 第一章\n\n## 1.1 基础概念\n\n### 1.1.1 小节一\n\n" + "跨章重复段落" * 60,
            ),
            ChapterContent(
                chapter_id=2,
                title="第二章",
                markdown="# 第2章 第二章\n\n## 2.1 平台设计\n\n### 2.1.1 小节二\n\n" + "跨章重复段落" * 60,
            ),
        ],
    )


def test_publication_audit_flags_duplicate_and_unresolved_foreshadow() -> None:
    state = _state_for_audit()
    state.quality.forbid_unresolved_final_review = True
    state.foreshadows = [
        ForeshadowItem(id="F001", description="后文需要回收", planted_chapter=1, planned_resolve_chapter=2)
    ]

    report = summarize_publication_audit(state)

    assert report["pass"] is False
    codes = {item["code"] for item in report["issues"]}
    assert "content.duplicate_paragraph" in codes
    assert "foreshadow.unresolved" in codes
    assert report["revise_chapters"]


def test_publication_audit_passes_complete_clean_book() -> None:
    state = _state_for_audit()
    state.chapters = [
        ChapterContent(
            chapter_id=1,
            title="第一章",
            markdown="# 第1章 第一章\n\n## 1.1 基础概念\n\n### 1.1.1 小节一\n\n第一章给出设备接入边界和工程取舍。",
        ),
        ChapterContent(
            chapter_id=2,
            title="第二章",
            markdown="# 第2章 第二章\n\n## 2.1 平台设计\n\n### 2.1.1 小节二\n\n第二章讨论平台层设计和运维方法。",
        ),
    ]

    issues = audit_publication_readiness(state)

    assert issues == []


def test_publication_audit_blocks_missing_secondary_heading() -> None:
    state = _state_for_audit()
    state.chapters[0].markdown = "# 第1章 第一章\n\n### 1.1.1 小节一\n\n正文。"

    issues = audit_publication_readiness(state)

    assert any(issue.code == "chapter.heading.h2_missing" and issue.chapter_id == 1 for issue in issues)


def test_publication_audit_blocks_conflicting_parent_titles() -> None:
    state = _state_for_audit()
    chapter = state.get_all_chapters_flat()[0]
    chapter.sections.append(
        SectionPlan(
            id="1.1.2",
            chapter_id=1,
            title="小节二",
            heading="1.1.2 小节二",
            parent_title="冲突标题",
            status="reviewed",
        )
    )
    state.section_contents.append(
        SectionContent(section_id="1.1.2", chapter_id=1, title="小节二", markdown="### 1.1.2 小节二\n\n正文。")
    )

    issues = audit_publication_readiness(state)

    assert any(issue.code == "chapter.heading.invalid_plan" and issue.chapter_id == 1 for issue in issues)


def test_publication_audit_blocks_misordered_heading_skeleton() -> None:
    state = _state_for_audit()
    chapter = state.get_all_chapters_flat()[0]
    chapter.sections.append(
        SectionPlan(
            id="1.2.1",
            chapter_id=1,
            title="小节二",
            heading="1.2.1 小节二",
            parent_title="进阶概念",
            status="reviewed",
        )
    )
    state.section_contents.append(
        SectionContent(section_id="1.2.1", chapter_id=1, title="小节二", markdown="### 1.2.1 小节二\n\n正文。")
    )
    state.chapters[0].markdown = """# 第1章 第一章

## 1.1 基础概念

## 1.2 进阶概念

### 1.1.1 小节一

正文。

### 1.2.1 小节二

正文。
"""

    issues = audit_publication_readiness(state)

    assert any(issue.code == "chapter.heading.skeleton_order" and issue.chapter_id == 1 for issue in issues)
