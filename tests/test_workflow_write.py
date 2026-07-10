from __future__ import annotations

from types import SimpleNamespace

from core.state import BookState, ChapterContent, ChapterPlan, PartPlan, QualitySettings, SectionContent, SectionPlan
from core.workflow import BookProject


def _state_with_sections() -> BookState:
    return BookState(
        parts=[
            PartPlan(
                name="基础篇",
                prefix="一",
                chapters=[
                    ChapterPlan(
                        id=1,
                        title="第一章",
                        sections=[
                            SectionPlan(id="1.1.1", chapter_id=1, title="一", heading="1.1.1 一"),
                            SectionPlan(id="1.1.2", chapter_id=1, title="二", heading="1.1.2 二"),
                            SectionPlan(id="1.2.1", chapter_id=1, title="三", heading="1.2.1 三"),
                        ],
                    ),
                    ChapterPlan(
                        id=2,
                        title="第二章",
                        sections=[SectionPlan(id="2.1.1", chapter_id=2, title="四", heading="2.1.1 四")],
                    ),
                ],
            )
        ],
        current_section_id="1.1.2",
    )


def test_write_target_resolution_accepts_human_scopes() -> None:
    project = object.__new__(BookProject)
    state = _state_with_sections()

    assert [item.id for item in project._resolve_write_target_sections(state, "current")] == ["1.1.2"]
    assert [item.id for item in project._resolve_write_target_sections(state, "1")] == ["1.1.1", "1.1.2", "1.2.1"]
    assert [item.id for item in project._resolve_write_target_sections(state, "1.1")] == ["1.1.1", "1.1.2"]
    assert [item.id for item in project._resolve_write_target_sections(state, "1.1.1")] == ["1.1.1"]
    assert [item.id for item in project._resolve_write_target_sections(state, "all")] == [
        "1.1.1",
        "1.1.2",
        "1.2.1",
        "2.1.1",
    ]


def test_parallel_chapters_only_for_complete_multi_chapter_targets() -> None:
    project = object.__new__(BookProject)
    state = _state_with_sections()
    state.writing.parallel_chapters = True
    state.writing.parallel_workers = 3

    assert project._should_parallelize_chapters(state, project._resolve_write_target_sections(state, "all")) is True
    assert project._should_parallelize_chapters(state, project._resolve_write_target_sections(state, "1")) is False
    assert project._should_parallelize_chapters(state, project._resolve_write_target_sections(state, "1.1")) is False


class _PassingCheck:
    def check(self, state: BookState) -> dict[str, object]:
        return {"pass": True, "issues": []}


class _PassingReview:
    def review(self, state: BookState) -> dict[str, object]:
        return {"pass": True, "issues": [], "foreshadow_checks": []}


class _ParallelWriter:
    def write_planned_section(self, state: BookState, section: SectionPlan, previous_brief: str = "") -> str:
        return f"### {section.heading}\n\n{section.id} " + "正文" * 120


class _NoopResearcher:
    def search(self, state: BookState) -> list[object]:
        return []

    def build_dossier(self, state: BookState, chunks: list[object]) -> None:
        return None


class _FailingCheck:
    def check(self, state: BookState) -> dict[str, object]:
        return {"pass": False, "issues": [{"code": "fact.missing", "message": "缺少事实依据"}]}


class _FailingDirector:
    def final_review(self, state: BookState) -> dict[str, object]:
        return {
            "pass": False,
            "overall_score": 6,
            "revise_chapters": [{"chapter_id": 1, "reason": "第一章深度不足"}],
            "summary": "未达到出版标准",
        }


class _Expander:
    def __init__(self) -> None:
        self.calls = 0

    def expand(self, state: BookState, markdown: str, feedback: str = "") -> str:
        self.calls += 1
        return "# 第1章 第一章\n\n" + "正文" * 30


class _Assembler:
    def assemble(self, state: BookState, raw_markdown: str) -> str:
        return raw_markdown


class _UnusedWriter:
    def __init__(self) -> None:
        self.section_revision_calls: list[str] = []

    def revise(self, state: BookState, feedback: str) -> str:
        raise AssertionError("deterministic short chapter should be fixed by expander")

    def revise_planned_section(
            self,
            state: BookState,
            section: SectionPlan,
            markdown: str,
            feedback: str,
            previous_brief: str = "",
    ) -> str:
        self.section_revision_calls.append(section.id)
        return f"{markdown}\n\n已按质量门反馈修订。"


class _CleanDirector:
    def final_review(self, state: BookState) -> dict[str, object]:
        return {"pass": True, "overall_score": 9, "revise_chapters": [], "summary": "通过"}


class _NoHitRAG:
    """原创性门用的假 RAG：从不返回命中，并记录检索次数。"""

    def __init__(self) -> None:
        self.calls = 0

    def retrieve(self, query: str, top_k: int = 3, *, categories: object = None) -> list:
        self.calls += 1
        return []


def _quality_project(tmp_path) -> BookProject:
    project = object.__new__(BookProject)
    project.paths = SimpleNamespace(project_dir=tmp_path, data_dir=tmp_path)
    project.cfg = SimpleNamespace(references=SimpleNamespace(query_categories=[]))
    project.rag = _NoHitRAG()
    project.expander = _Expander()
    project.writer = _UnusedWriter()
    project.assembler = _Assembler()
    project.fact_checker = _PassingCheck()
    project.citation_guard = _PassingCheck()
    project.style_guard = _PassingCheck()
    project.editor = _PassingReview()
    project.director = _CleanDirector()
    return project


def test_parallel_chapters_write_and_merge_by_chapter(tmp_path) -> None:
    project = object.__new__(BookProject)
    project.paths = SimpleNamespace(project_dir=tmp_path, data_dir=tmp_path)
    project.cfg = SimpleNamespace(references=SimpleNamespace(query_categories=[]))
    project.rag = _NoHitRAG()
    project.writer = _ParallelWriter()
    project.assembler = _Assembler()
    project.researcher = _NoopResearcher()
    project.fact_checker = _PassingCheck()
    project.citation_guard = _PassingCheck()
    project.style_guard = _PassingCheck()
    project.editor = _PassingReview()
    project.director = _CleanDirector()
    project._new_worker_project = lambda: project
    project._save_write_checkpoint = lambda thread_id, state: None
    project.write_status = lambda thread_id: {"thread_id": thread_id, "has_checkpoint": True}
    state = _state_with_sections()
    for section in state.get_all_sections_flat():
        section.target_words = 1
    state.quality = QualitySettings(enabled=False, min_figures_per_section=0)
    state.writing.parallel_chapters = True
    state.writing.parallel_workers = 2

    status = project._write_chapters_parallel(state, state.get_all_sections_flat(), "book", "all")

    assert status["parallel_chapters"] is True
    assert status["chapters_processed"] == 2
    assert status["sections_processed"] == 4
    assert len(state.section_contents) == 4
    assert {content.chapter_id for content in state.chapters} == {1, 2}


def test_chapter_quality_gate_revises_short_chapter_then_approves(tmp_path) -> None:
    project = _quality_project(tmp_path)
    state = _state_with_sections()
    state.quality = QualitySettings(enabled=True, min_words_per_chapter=20)
    state.max_revision_count = 1
    state.set_current_chapter_by_id(1)
    state.upsert_chapter_content(ChapterContent(chapter_id=1, title="第一章", markdown="# 短"))

    content = project._review_chapter_until_pass(state, 1)

    assert project.expander.calls == 1
    assert content.revision_count == 1
    assert state.get_chapter_content(1).fact_feedback == ""
    assert state.get_chapter_content(1).review_feedback == ""
    assert state.get_current_chapter().status == "approved"


def test_originality_skipped_when_deterministic_gate_fails(tmp_path) -> None:
    # 确定性门必然失败（字数远低于下限）时，不应触发昂贵的原创性检索
    project = _quality_project(tmp_path)
    state = _state_with_sections()
    state.quality = QualitySettings(enabled=True, min_words_per_chapter=100000, originality_check_enabled=True)
    state.max_revision_count = 0
    state.set_current_chapter_by_id(1)
    state.upsert_chapter_content(ChapterContent(chapter_id=1, title="第一章", markdown="# 短"))

    project._review_chapter_until_pass(state, 1)

    assert project.rag.calls == 0  # 确定性门失败，原创性检索被跳过
    assert state.get_current_chapter().status == "quality_failed"


def test_section_review_marks_failed_and_continues_at_revision_limit(tmp_path) -> None:
    project = _quality_project(tmp_path)
    state = _state_with_sections()
    state.quality = QualitySettings(continue_on_failure=True)
    state.max_revision_count = 0
    section = state.get_section_plan("1.1.1")
    assert section is not None
    content = SectionContent(section_id="1.1.1", chapter_id=1, title="一", markdown="短", word_count=1)

    reviewed = project._review_section_until_pass(state, section, content, "", "book")

    assert reviewed.revision_count == 0
    assert "section.too_short" in reviewed.review_feedback
    assert section.status == "review_failed"


def test_section_review_requires_book_figure(tmp_path) -> None:
    project = _quality_project(tmp_path)
    state = _state_with_sections()
    state.quality = QualitySettings(min_figures_per_section=1, continue_on_failure=True)
    state.max_revision_count = 0
    section = state.get_section_plan("1.1.1")
    assert section is not None
    section.target_words = 1
    content = SectionContent(section_id="1.1.1", chapter_id=1, title="一", markdown="### 1.1.1 一\n\n正文", word_count=2)

    reviewed = project._review_section_until_pass(state, section, content, "", "book")

    assert "section.missing_book_figure" in reviewed.review_feedback
    assert section.status == "review_failed"


def test_chapter_deterministic_gate_marks_failed_and_continues_at_revision_limit(tmp_path) -> None:
    project = _quality_project(tmp_path)
    state = _state_with_sections()
    state.quality = QualitySettings(enabled=True, min_words_per_chapter=100, continue_on_failure=True)
    state.max_revision_count = 0
    state.set_current_chapter_by_id(1)
    state.upsert_chapter_content(ChapterContent(chapter_id=1, title="第一章", markdown="# 第一章\n\n短", word_count=1))

    content = project._review_chapter_until_pass(state, 1)

    assert content.revision_count == 0
    assert "word_count.too_short" in content.publication_feedback
    chapter = state.get_current_chapter()
    assert chapter is not None
    assert chapter.status == "quality_failed"


def test_chapter_quality_gate_revises_targeted_sections_before_chapter_fallback(tmp_path) -> None:
    project = _quality_project(tmp_path)
    state = _state_with_sections()
    state.quality = QualitySettings(enabled=True, min_words_per_chapter=1, min_figures_per_section=1)
    state.max_revision_count = 1
    state.set_current_chapter_by_id(1)
    state.upsert_section_content(
        SectionContent(
            section_id="1.1.1",
            chapter_id=1,
            title="一",
            markdown="### 1.1.1 一\n\n正文。",
        )
    )
    state.upsert_chapter_content(ChapterContent(chapter_id=1, title="第一章", markdown="# 第1章 第一章\n\n正文。"))

    content = project._review_chapter_until_pass(state, 1)

    assert project.expander.calls == 0
    assert project.writer.section_revision_calls == ["1.1.1"]
    assert content.revision_count == 1
    assert "已按质量门反馈修订" in state.get_section_content("1.1.1").markdown


def test_chapter_llm_gate_marks_failed_and_continues_at_revision_limit(tmp_path) -> None:
    project = _quality_project(tmp_path)
    project.fact_checker = _FailingCheck()
    state = _state_with_sections()
    state.quality = QualitySettings(enabled=True, min_words_per_chapter=1, continue_on_failure=True)
    state.max_revision_count = 0
    state.set_current_chapter_by_id(1)
    state.upsert_chapter_content(ChapterContent(chapter_id=1, title="第一章", markdown="# 第一章\n\n" + "正文" * 20))

    content = project._review_chapter_until_pass(state, 1)

    assert "fact.missing" in content.fact_feedback
    assert "事实核查" in content.revision_feedback
    chapter = state.get_current_chapter()
    assert chapter is not None
    assert chapter.status == "quality_failed"


def test_final_review_marks_report_and_continues_at_revision_limit(tmp_path) -> None:
    project = _quality_project(tmp_path)
    project.director = _FailingDirector()
    state = _state_with_sections()
    state.quality = QualitySettings(continue_on_failure=True)
    state.max_final_revision_round = 0
    state.upsert_chapter_content(ChapterContent(chapter_id=1, title="第一章", markdown="# 第一章\n\n正文"))
    state.upsert_chapter_content(ChapterContent(chapter_id=2, title="第二章", markdown="# 第二章\n\n正文"))

    project._final_review_if_ready(state)

    assert state.publication_approved is False
    assert state.final_revision_chapters == [1]
    assert "未达到出版标准" in state.final_report


def test_quality_failure_status_helpers_return_feedback() -> None:
    project = object.__new__(BookProject)
    state = _state_with_sections()
    section = state.get_section_plan("1.1.1")
    assert section is not None
    section.status = "review_failed"
    state.upsert_section_content(
        SectionContent(section_id="1.1.1", chapter_id=1, title="一", markdown="短", revision_feedback="小节太短")
    )
    chapter = state.get_current_chapter()
    assert chapter is not None
    chapter.status = "quality_failed"
    state.upsert_chapter_content(
        ChapterContent(chapter_id=1, title="第一章", markdown="# 第一章", publication_feedback="章节太短")
    )

    assert project._review_failed_sections(state)[0]["feedback"] == "小节太短"
    assert project._quality_failed_chapters(state)[0]["feedback"].startswith("## 出版确定性质量门")


def test_final_review_marks_completed_book_publication_approved(tmp_path) -> None:
    project = _quality_project(tmp_path)
    state = _state_with_sections()
    state.current_phase = "completed"
    state.upsert_chapter_content(ChapterContent(chapter_id=1, title="第一章", markdown="# 第一章\n\n正文"))
    state.upsert_chapter_content(ChapterContent(chapter_id=2, title="第二章", markdown="# 第二章\n\n正文"))

    project._final_review_if_ready(state)

    assert state.publication_approved is True
    assert '"pass": true' in state.final_report
