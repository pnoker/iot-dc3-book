from __future__ import annotations

from core.reference_markers import audit_reference_markers, clean_reference_markers, transform_reference_markers
from core.state import (
    BookState,
    ChapterContent,
    ChapterPlan,
    EvidenceNote,
    PartPlan,
    ResearchDossier,
    SectionContent,
    SectionPlan,
)


def _state_with_references() -> BookState:
    dossier = ResearchDossier(
        chapter_id=1,
        evidence_notes=[
            EvidenceNote(id="S1", source_type="local", source="物联网教材.pdf", locator="第2章", excerpt="NB-IoT 适合低功耗广覆盖场景。"),
            EvidenceNote(id="W1", source_type="web", source="标准说明", locator="https://example.com", excerpt="Release 17 增强了相关能力。"),
        ],
    )
    chapter = ChapterPlan(
        id=1,
        title="连接技术",
        sections=[SectionPlan(id="1.1.1", chapter_id=1, title="NB-IoT", heading="1.1.1 NB-IoT")],
        research_dossier=dossier,
    )
    markdown = """# 第1章 连接技术

### 1.1.1 NB-IoT

NB-IoT 适合低功耗广覆盖场景。（资料：[S1]）

Release 17 有增强。（资料：[W1]）

这个引用不存在。（资料：[S9]）
"""
    return BookState(
        parts=[PartPlan(name="基础篇", prefix="一", chapters=[chapter])],
        section_contents=[SectionContent(section_id="1.1.1", chapter_id=1, title="NB-IoT", markdown=markdown)],
        chapters=[ChapterContent(chapter_id=1, title="连接技术", markdown=markdown)],
    )


def test_audit_reference_markers_reports_missing_ids() -> None:
    result = audit_reference_markers(_state_with_references()).to_dict()

    assert result["marker_count"] == 3
    assert result["reference_count"] == 3
    assert result["missing_count"] == 1
    chapter = result["chapters"][0]
    assert chapter["unique_reference_ids"] == ["S1", "S9", "W1"]
    assert chapter["missing_reference_ids"] == ["S9"]


def test_transform_reference_markers_remove_mode() -> None:
    state = _state_with_references()
    dossier = state.get_all_chapters_flat()[0].research_dossier

    result = transform_reference_markers(state.chapters[0].markdown, dossier=dossier, mode="remove")

    assert "资料：[" not in result.markdown
    assert result.before_markers == 3
    assert result.after_markers == 0
    assert "NB-IoT 适合低功耗广覆盖场景。" in result.markdown


def test_transform_reference_markers_footnote_mode() -> None:
    state = _state_with_references()
    dossier = state.get_all_chapters_flat()[0].research_dossier

    result = transform_reference_markers(state.chapters[0].markdown, dossier=dossier, mode="footnote")

    assert "（资料：[S1]）" not in result.markdown
    assert "NB-IoT 适合低功耗广覆盖场景。[^1]" in result.markdown
    assert "#### 参考注释" in result.markdown
    assert "[^1]: S1：物联网教材.pdf，第2章。" in result.markdown
    assert "[^3]: S9：未在当前章节研究资料包中找到对应来源。" in result.markdown


def test_transform_reference_markers_endnote_mode() -> None:
    state = _state_with_references()
    dossier = state.get_all_chapters_flat()[0].research_dossier

    result = transform_reference_markers(state.chapters[0].markdown, dossier=dossier, mode="endnote")

    assert "NB-IoT 适合低功耗广覆盖场景。[1]" in result.markdown
    assert "#### 参考文献说明" in result.markdown
    assert "1. S1：物联网教材.pdf，第2章。" in result.markdown
    assert result.endnote_count == 3


def test_clean_reference_markers_updates_sections_and_chapters() -> None:
    state = _state_with_references()

    result = clean_reference_markers(state, mode="remove")

    assert result.marker_count_before == 6
    assert result.marker_count_after == 0
    assert len(result.changed_files) == 2
    assert "资料：[" not in state.section_contents[0].markdown
    assert "资料：[" not in state.chapters[0].markdown
