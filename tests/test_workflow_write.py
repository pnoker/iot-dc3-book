from __future__ import annotations

import json
import os
from copy import deepcopy
from types import SimpleNamespace

import pytest

from core.config import config_to_app_config
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


def _mark_book_ready_for_final_review(state: BookState) -> None:
    for chapter in state.get_all_chapters_flat():
        chapter.status = "approved"
        for section in chapter.sections:
            section.status = "reviewed"
            if state.get_section_content(section.id) is None:
                state.upsert_section_content(
                    SectionContent(
                        section_id=section.id,
                        chapter_id=chapter.id,
                        title=section.title,
                        markdown=f"### {section.heading}\n\n正文",
                    )
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
    def __init__(self) -> None:
        self.calls: list[str] = []

    def write_planned_section(self, state: BookState, section: SectionPlan, previous_brief: str = "") -> str:
        self.calls.append(section.id)
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


class _ShrinkingExpander:
    def expand(self, state: BookState, markdown: str, feedback: str = "") -> str:
        return "```markdown\n# 第1章 第一章\n\n过短摘要。\n```"


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


class _FactFixingSectionWriter(_UnusedWriter):
    def revise_planned_section(
            self,
            state: BookState,
            section: SectionPlan,
            markdown: str,
            feedback: str,
            previous_brief: str = "",
    ) -> str:
        self.section_revision_calls.append(section.id)
        return f"### {section.heading}\n\n" + "正文" * 700 + "\n\n在示意场景中，平台延迟保持在较低水平，市场判断改为定性描述。"


class _SuccessfulSectionReviser:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def revise_planned_section(
            self,
            state: BookState,
            section: SectionPlan,
            markdown: str,
            feedback: str,
            previous_brief: str = "",
    ) -> str:
        self.calls.append(section.id)
        return f"### {section.heading}\n\n{section.id} " + "正文" * 220


class _CleanDirector:
    def final_review(self, state: BookState) -> dict[str, object]:
        return {"pass": True, "overall_score": 9, "revise_chapters": [], "summary": "通过"}


class _UnexpectedDirector:
    def final_review(self, state: BookState) -> dict[str, object]:
        raise AssertionError("deterministic publication audit should run before LLM final review")


class _NoHitRAG:
    """原创性门用的假 RAG：从不返回命中，并记录检索次数。"""

    def __init__(self) -> None:
        self.calls = 0

    def retrieve_sparse(self, query: str, top_k: int = 3, *, categories: object = None) -> list:
        self.calls += 1
        return []


def _quality_project(tmp_path) -> BookProject:
    project = object.__new__(BookProject)
    project.paths = SimpleNamespace(project_dir=tmp_path, data_dir=tmp_path)
    project.cfg = SimpleNamespace(quality=QualitySettings(enabled=False, min_figures_per_section=0), references=SimpleNamespace(query_categories=[]))
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


def _workflow_app_config():
    return config_to_app_config(
        {
            "book": {"title": "Test", "subtitle": "Sub"},
            "parts": [
                {
                    "name": "Part1",
                    "prefix": "一",
                    "chapters": [{"id": 1, "title": "Ch1", "summary": "Summary"}],
                }
            ],
            "style": {
                "tone": "面向 IoT 工程师和架构师的工程著作口吻",
                "chapter_structure": ["按工程判断自然收束，不强制本章小结"],
            },
            "writing": {"parallel_workers": 2},
            "quality": {
                "require_summary": False,
                "min_figures_per_section": 0,
                "max_revision_rounds": 2,
                "max_final_revision_rounds": 1,
            },
            "llm": {
                "base_url": "https://example.test",
                "api_key": "test-chat-key",
                "model": "model",
                "embedding": {
                    "base_url": "https://embed.test",
                    "api_key": "test-embed-key",
                    "model": "embed-model",
                },
            },
            "references": {"sources": [{"path": "../books", "label": "books", "categories": ["iot"]}]},
        }
    )


def test_load_write_checkpoint_refreshes_runtime_settings_from_current_config(tmp_path) -> None:
    project = object.__new__(BookProject)
    project.paths = SimpleNamespace(project_dir=tmp_path, data_dir=tmp_path)
    project.cfg = _workflow_app_config()
    checkpoint_state = _state_with_sections()
    checkpoint_state.style.tone = "旧教材口吻"
    checkpoint_state.style.chapter_structure = ["必须写本章小结"]
    checkpoint_state.writing.parallel_workers = 9
    checkpoint_state.quality = QualitySettings(require_summary=True, min_figures_per_section=1, max_revision_rounds=9)
    checkpoint_state.max_revision_count = 9

    project._save_write_checkpoint("book", checkpoint_state)

    loaded = project.load_write_checkpoint("book")

    assert loaded.style.tone == project.cfg.style.tone
    assert loaded.style.chapter_structure == project.cfg.style.chapter_structure
    assert loaded.writing.parallel_workers == project.cfg.writing.parallel_workers
    assert loaded.quality.require_summary is False
    assert loaded.quality.min_figures_per_section == 0
    assert loaded.max_revision_count == project.cfg.quality.max_revision_rounds
    assert loaded.get_section_plan("1.1.1") is not None


def test_parallel_chapters_write_and_merge_by_chapter(tmp_path) -> None:
    project = object.__new__(BookProject)
    project.paths = SimpleNamespace(project_dir=tmp_path, data_dir=tmp_path)
    project.cfg = SimpleNamespace(quality=QualitySettings(enabled=False, min_figures_per_section=0), references=SimpleNamespace(query_categories=[]))
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


def test_parallel_worker_does_not_write_manuscript_before_merge(tmp_path) -> None:
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
    state = _state_with_sections()
    for section in state.get_all_sections_flat():
        section.target_words = 1
    state.quality = QualitySettings(enabled=False, min_figures_per_section=0)

    isolated = project._write_chapter_in_isolated_state(state, 1, "book")

    assert isolated.get_chapter_content(1) is not None
    assert not (tmp_path / "manuscript").exists()

    project._merge_chapter_state(state, isolated, 1)
    project._save_chapter_artifacts(state, 1)

    assert (tmp_path / "manuscript" / "chapter-01" / "1.1.1.md").exists()
    assert (tmp_path / "manuscript" / "chapter-01" / "chapter.md").exists()


def test_parallel_worker_checkpoint_persists_isolated_progress(tmp_path) -> None:
    project = object.__new__(BookProject)
    project.paths = SimpleNamespace(project_dir=tmp_path, data_dir=tmp_path)
    project.cfg = SimpleNamespace(
        quality=QualitySettings(enabled=False, min_figures_per_section=0),
        references=SimpleNamespace(query_categories=[]),
    )
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
    state = _state_with_sections()
    for section in state.get_all_sections_flat():
        section.target_words = 1
    state.quality = QualitySettings(enabled=False, min_figures_per_section=0)

    project._write_chapter_in_isolated_state(state, 1, "book")

    worker_checkpoint = project.worker_checkpoint_path("book", 1)
    assert worker_checkpoint.exists()
    recovered = project._load_worker_checkpoint("book", 1)
    assert recovered.get_chapter_content(1) is not None
    assert recovered.get_section_content("1.1.1") is not None
    assert not (tmp_path / "manuscript").exists()


def test_parallel_worker_resumes_from_worker_checkpoint(tmp_path) -> None:
    project = object.__new__(BookProject)
    project.paths = SimpleNamespace(project_dir=tmp_path, data_dir=tmp_path)
    project.cfg = SimpleNamespace(
        quality=QualitySettings(enabled=False, min_figures_per_section=0),
        references=SimpleNamespace(query_categories=[]),
    )
    project.rag = _NoHitRAG()
    writer = _ParallelWriter()
    project.writer = writer
    project.assembler = _Assembler()
    project.researcher = _NoopResearcher()
    project.fact_checker = _PassingCheck()
    project.citation_guard = _PassingCheck()
    project.style_guard = _PassingCheck()
    project.editor = _PassingReview()
    project.director = _CleanDirector()
    project._new_worker_project = lambda: project
    checkpoint_state = _state_with_sections()
    for section in checkpoint_state.get_all_sections_flat():
        section.target_words = 1
    checkpoint_state.quality = QualitySettings(enabled=False, min_figures_per_section=0)
    checkpoint_state.upsert_section_content(
        SectionContent(section_id="1.1.1", chapter_id=1, title="一", markdown="### 1.1.1 一\n\n已有正文", word_count=10)
    )
    checkpoint_state.mark_section_status("1.1.1", "reviewed")
    project._save_state_envelope(project.worker_checkpoint_path("book", 1), checkpoint_state, kind="write.worker.checkpoint")

    fresh_snapshot = _state_with_sections()
    for section in fresh_snapshot.get_all_sections_flat():
        section.target_words = 1
    fresh_snapshot.quality = QualitySettings(enabled=False, min_figures_per_section=0)
    recovered = project._write_chapter_in_isolated_state(fresh_snapshot, 1, "book")

    assert recovered.get_section_content("1.1.1").markdown == "### 1.1.1 一\n\n已有正文"
    assert "1.1.1" not in writer.calls
    assert {"1.1.2", "1.2.1"}.issubset(set(writer.calls))


def test_read_status_overlays_newer_worker_checkpoint(tmp_path) -> None:
    project = object.__new__(BookProject)
    project.paths = SimpleNamespace(project_dir=tmp_path, data_dir=tmp_path)
    project.cfg = SimpleNamespace(
        quality=QualitySettings(enabled=False, min_figures_per_section=0),
        references=SimpleNamespace(query_categories=[]),
    )
    main_state = _state_with_sections()
    main_state.upsert_section_content(
        SectionContent(section_id="1.1.1", chapter_id=1, title="一", markdown="### 1.1.1 一\n\n主正文")
    )
    main_state.mark_section_status("1.1.1", "written")
    project._save_write_checkpoint("book", main_state)

    worker_state = deepcopy(main_state)
    worker_state.mark_section_status("1.1.1", "reviewed")
    worker_state.upsert_section_content(
        SectionContent(section_id="1.1.1", chapter_id=1, title="一", markdown="### 1.1.1 一\n\nworker正文")
    )
    project._save_state_envelope(project.worker_checkpoint_path("book", 1), worker_state, kind="write.worker.checkpoint")
    project._save_write_checkpoint("book", main_state)

    displayed = project.load_write_checkpoint_with_workers("book")
    main_reloaded = project.load_write_checkpoint("book")

    assert displayed.get_section_plan("1.1.1").status == "reviewed"
    assert displayed.get_section_content("1.1.1").markdown.endswith("worker正文")
    assert main_reloaded.get_section_plan("1.1.1").status == "written"
    assert main_reloaded.get_section_content("1.1.1").markdown.endswith("主正文")


def test_interrupt_shutdown_waits_through_repeated_ctrl_c() -> None:
    class InterruptingExecutor:
        def __init__(self) -> None:
            self.calls = 0

        def shutdown(self, *, wait: bool, cancel_futures: bool) -> None:
            self.calls += 1
            assert wait is True
            assert cancel_futures is True
            if self.calls == 1:
                raise KeyboardInterrupt

    executor = InterruptingExecutor()

    BookProject._shutdown_executor_after_interrupt(executor)  # type: ignore[arg-type]

    assert executor.calls == 2


def test_parallel_worker_retries_review_failed_sections(tmp_path) -> None:
    project = object.__new__(BookProject)
    project.paths = SimpleNamespace(project_dir=tmp_path, data_dir=tmp_path)
    project.cfg = SimpleNamespace(
        quality=QualitySettings(enabled=False, min_figures_per_section=0),
        references=SimpleNamespace(query_categories=[]),
    )
    project.rag = _NoHitRAG()
    writer = _SuccessfulSectionReviser()
    project.writer = writer
    project.assembler = _Assembler()
    project.fact_checker = _PassingCheck()
    project.citation_guard = _PassingCheck()
    project.style_guard = _PassingCheck()
    project.editor = _PassingReview()
    project.director = _CleanDirector()
    project._new_worker_project = lambda: project
    state = _state_with_sections()
    state.quality = QualitySettings(enabled=False, min_figures_per_section=0)
    for section in state.get_all_sections_flat():
        section.target_words = 1
        state.upsert_section_content(
            SectionContent(section_id=section.id, chapter_id=section.chapter_id, title=section.title, markdown=f"### {section.heading}\n\n已有正文" * 40)
        )
        state.mark_section_status(section.id, "reviewed")
    failed = state.get_section_plan("1.1.1")
    assert failed is not None
    failed.status = "review_failed"

    recovered = project._write_chapter_in_isolated_state(state, 1, "book")

    assert writer.calls == ["1.1.1"]
    assert recovered.get_section_plan("1.1.1").status == "reviewed"


def test_write_lock_rejects_live_process(tmp_path) -> None:
    project = object.__new__(BookProject)
    project.paths = SimpleNamespace(data_dir=tmp_path)
    lock_path = project.write_lock_path("book")
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text(
        json.dumps({"pid": os.getpid(), "operation": "write.resume", "started_at": "now", "token": "active"}),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="已有写作任务正在运行"), project._write_operation_lock("book", "write.resume"):
        pass


def test_write_lock_cleans_stale_process_lock(tmp_path) -> None:
    project = object.__new__(BookProject)
    project.paths = SimpleNamespace(data_dir=tmp_path)
    lock_path = project.write_lock_path("book")
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text(
        json.dumps({"pid": -1, "operation": "write.resume", "started_at": "old", "token": "stale"}),
        encoding="utf-8",
    )

    with project._write_operation_lock("book", "write.resume"):
        assert lock_path.exists()

    assert not lock_path.exists()


def test_worker_project_uses_runtime_config_snapshot(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    cfg = SimpleNamespace(name="snapshot")
    project = object.__new__(BookProject)
    project.config_path = "config"
    project.cfg = cfg

    def fake_init(self, config_path: str = "config", *, cfg: object | None = None) -> None:
        calls.append((config_path, cfg))

    monkeypatch.setattr(BookProject, "__init__", fake_init)

    project._new_worker_project()

    assert calls == [("config", cfg)]


def test_recover_manuscript_imports_orphan_sections_and_chapters(tmp_path) -> None:
    project = object.__new__(BookProject)
    project.paths = SimpleNamespace(project_dir=tmp_path, data_dir=tmp_path)
    project.cfg = SimpleNamespace(quality=QualitySettings())
    state = _state_with_sections()
    state.quality = QualitySettings(enabled=False, min_figures_per_section=0)
    state.upsert_section_content(
        SectionContent(section_id="1.1.1", chapter_id=1, title="一", markdown="### 1.1.1 一\n\n已有正文")
    )
    project._save_write_checkpoint("book", state)
    chapter_dir = tmp_path / "manuscript" / "chapter-01"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "1.1.2.md").write_text("### 1.1.2 二\n\n" + "正文" * 120, encoding="utf-8")
    (chapter_dir / "1.2.1.md").write_text("### 1.2.1 三\n\n" + "正文" * 120, encoding="utf-8")
    (chapter_dir / "chapter.md").write_text("# 第1章 第一章\n\n" + "正文" * 120, encoding="utf-8")

    result = project.recover_manuscript("book")
    recovered = project.load_write_checkpoint("book")

    assert result["sections_recovered"] == 2
    assert result["chapters_recovered"] == 1
    assert result["current_section"] == "2.1.1"
    assert recovered.get_section_content("1.1.2") is not None
    assert recovered.get_section_content("1.2.1") is not None
    assert recovered.get_chapter_content(1) is not None
    assert recovered.current_section_id == "2.1.1"
    assert result["backup"] is not None


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


def test_section_review_persists_reviewed_checkpoint(tmp_path) -> None:
    project = _quality_project(tmp_path)
    state = _state_with_sections()
    state.quality = QualitySettings(min_figures_per_section=0)
    state.max_revision_count = 0
    section = state.get_section_plan("1.1.1")
    assert section is not None
    section.target_words = 1
    markdown = f"### {section.heading}\n\n" + "正文" * 220
    content = SectionContent(section_id="1.1.1", chapter_id=1, title="一", markdown=markdown, word_count=440)
    state.mark_section_status("1.1.1", "written")
    state.upsert_section_content(content)
    project._save_write_checkpoint("book", state)

    project._review_section_until_pass(state, section, content, "", "book")
    reloaded = project.load_write_checkpoint("book")

    assert reloaded.get_section_plan("1.1.1").status == "reviewed"
    assert reloaded.get_section_content("1.1.1").review_feedback == ""


def test_write_resume_retries_review_failed_section(tmp_path) -> None:
    project = _quality_project(tmp_path)
    project.cfg = SimpleNamespace(quality=QualitySettings(min_figures_per_section=0), references=SimpleNamespace(query_categories=[]))
    writer = _SuccessfulSectionReviser()
    project.writer = writer
    state = _state_with_sections()
    state.quality = QualitySettings(min_figures_per_section=0)
    section = state.get_section_plan("1.1.1")
    assert section is not None
    section.status = "review_failed"
    section.target_words = 1
    state.upsert_section_content(
        SectionContent(
            section_id="1.1.1",
            chapter_id=1,
            title="一",
            markdown="短",
            revision_feedback='{"issues":[{"code":"section.too_short","section_id":"1.1.1"}]}',
        )
    )
    project._save_write_checkpoint("book", state)

    status = project.write_resume("book", target="1.1.1")
    recovered = project.load_write_checkpoint("book")

    assert status["sections_processed"] == 1
    assert writer.calls == ["1.1.1"]
    assert recovered.get_section_plan("1.1.1").status == "reviewed"


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


def test_normalize_markdown_output_unwraps_outer_markdown_fence() -> None:
    markdown = "```markdown\n# 标题\n\n正文\n```"

    assert BookProject._normalize_markdown_output(markdown) == "# 标题\n\n正文"


def test_normalize_markdown_output_strips_explanation_before_unclosed_fence() -> None:
    markdown = "好的，以下是合稿后的完整章节。\n\n```markdown\n# 第5章 标题\n\n正文\n\n```book-figure\nid: fig-1\n```"

    normalized = BookProject._normalize_markdown_output(markdown)

    assert normalized.startswith("# 第5章 标题")
    assert "好的" not in normalized
    assert "```markdown" not in normalized
    assert "```book-figure" in normalized


def test_chapter_revision_rejects_catastrophic_shrink(tmp_path) -> None:
    project = _quality_project(tmp_path)
    project.expander = _ShrinkingExpander()
    state = _state_with_sections()
    state.quality = QualitySettings(enabled=True, min_words_per_chapter=9000)
    state.set_current_chapter_by_id(1)
    original = "# 第1章 第一章\n\n" + "这是完整章节正文。" * 1200
    content = ChapterContent(chapter_id=1, title="第一章", markdown=original, word_count=10806)
    state.upsert_chapter_content(content)

    revised = project._revise_chapter_from_feedback(state, content, "反馈", 1)

    assert revised.markdown == original
    assert revised.word_count == 10806
    assert revised.revision_count == 1


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
    assert project.writer.section_revision_calls == ["1.1.1", "1.1.1"]
    assert content.revision_count == 1
    assert "已按质量门反馈修订" in state.get_section_content("1.1.1").markdown
    assert state.get_section_plan("1.1.1").status == "review_failed"


def test_chapter_fact_gate_revises_located_section_without_chapter_rewrite(tmp_path) -> None:
    project = _quality_project(tmp_path)
    writer = _FactFixingSectionWriter()
    project.writer = writer
    state = _state_with_sections()
    state.quality = QualitySettings(enabled=True, min_words_per_chapter=1, forbid_unsourced_statistics=True)
    state.max_revision_count = 1
    state.set_current_chapter_by_id(1)
    section = state.get_section_plan("1.1.1")
    assert section is not None
    markdown = f"### {section.heading}\n\n2023年，平台将端到端时延稳定控制在50ms，市场规模达到100亿元。" + "正文" * 700
    state.upsert_section_content(
        SectionContent(
            section_id="1.1.1",
            chapter_id=1,
            title="一",
            markdown=markdown,
            word_count=1400,
        )
    )
    state.upsert_chapter_content(ChapterContent(chapter_id=1, title="第一章", markdown=f"# 第1章 第一章\n\n{markdown}"))

    content = project._review_chapter_until_pass(state, 1)

    assert writer.section_revision_calls == ["1.1.1"]
    assert project.expander.calls == 0
    assert content.publication_feedback == ""
    assert state.get_current_chapter().status == "approved"


def test_chapter_targeted_revision_reviews_revised_section(tmp_path) -> None:
    project = _quality_project(tmp_path)
    state = _state_with_sections()
    state.quality = QualitySettings(enabled=False, min_figures_per_section=0)
    state.max_revision_count = 1
    state.set_current_chapter_by_id(1)
    section = state.get_section_plan("1.1.1")
    assert section is not None
    section.target_words = 1
    state.mark_section_status("1.1.1", "reviewed")
    state.upsert_section_content(
        SectionContent(
            section_id="1.1.1",
            chapter_id=1,
            title="一",
            markdown="### 1.1.1 一\n\n" + "正文" * 260,
            word_count=520,
        )
    )
    chapter_content = ChapterContent(chapter_id=1, title="第一章", markdown="# 第1章 第一章\n\n正文。")

    project._revise_sections_from_chapter_feedback(
        state,
        chapter_content,
        ["1.1.1"],
        '{"issues":[{"section_id":"1.1.1","description":"补强论述"}]}',
        1,
        thread_id=None,
    )

    assert project.writer.section_revision_calls == ["1.1.1"]
    assert state.get_section_plan("1.1.1").status == "reviewed"


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
    _mark_book_ready_for_final_review(state)
    state.upsert_chapter_content(ChapterContent(chapter_id=1, title="第一章", markdown="# 第一章\n\n正文"))
    state.upsert_chapter_content(ChapterContent(chapter_id=2, title="第二章", markdown="# 第二章\n\n正文"))

    project._final_review_if_ready(state)

    assert state.publication_approved is False
    assert state.final_revision_chapters == [1]
    assert "未达到出版标准" in state.final_report


def test_final_review_blocks_on_publication_audit_before_llm(tmp_path) -> None:
    project = _quality_project(tmp_path)
    project.director = _UnexpectedDirector()
    state = _state_with_sections()
    state.quality = QualitySettings(continue_on_failure=True)
    state.max_final_revision_round = 1
    state.upsert_chapter_content(ChapterContent(chapter_id=1, title="第一章", markdown="# 第一章\n\n正文"))
    state.upsert_chapter_content(ChapterContent(chapter_id=2, title="第二章", markdown="# 第二章\n\n正文"))

    project._final_review_if_ready(state)

    assert state.publication_approved is False
    assert "deterministic_publication_audit" in state.final_report
    assert state.final_revision_chapters


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
    _mark_book_ready_for_final_review(state)
    state.upsert_chapter_content(ChapterContent(chapter_id=1, title="第一章", markdown="# 第一章\n\n正文"))
    state.upsert_chapter_content(ChapterContent(chapter_id=2, title="第二章", markdown="# 第二章\n\n正文"))

    project._final_review_if_ready(state)

    assert state.publication_approved is True
    assert '"pass": true' in state.final_report


def test_write_export_rejects_unapproved_book(tmp_path) -> None:
    project = object.__new__(BookProject)
    project.paths = SimpleNamespace(project_dir=tmp_path, data_dir=tmp_path, output_dir=tmp_path / "output", figures_dir=tmp_path / ".data" / "figures")
    project.cfg = _workflow_app_config()
    project.cfg.quality.enabled = False
    project._write_checkpoint_path_override = None
    project._write_checkpoint_kind_override = None
    state = _state_with_sections()
    state.current_phase = "completed"
    _mark_book_ready_for_final_review(state)
    project._save_write_checkpoint("book-1", state)

    with pytest.raises(RuntimeError, match="publication_approved=false"):
        project.write_export("book-1", target="markdown")


def test_write_export_draft_allows_unapproved_preview(tmp_path) -> None:
    project = object.__new__(BookProject)
    project.paths = SimpleNamespace(project_dir=tmp_path, data_dir=tmp_path, output_dir=tmp_path / "output", figures_dir=tmp_path / ".data" / "figures")
    project.cfg = _workflow_app_config()
    project.cfg.quality.enabled = False
    project._write_checkpoint_path_override = None
    project._write_checkpoint_kind_override = None
    state = _state_with_sections()
    state.current_phase = "completed"
    _mark_book_ready_for_final_review(state)
    state.upsert_chapter_content(ChapterContent(chapter_id=1, title="第一章", markdown="# 第一章\n\n正文"))
    project._save_write_checkpoint("book-1", state)

    result = project.write_export("book-1", target="markdown", draft=True)

    assert result["draft"] is True
    assert result["publication_ready"] is False
    assert result["output_dir"] == str(tmp_path / "output" / "draft")
    assert result["book_markdown"] == str(tmp_path / "output" / "draft" / "book.md")
    assert "草稿导出" in result["warning"]
    assert (tmp_path / "output" / "draft" / "book.md").exists()


def test_write_export_markdown_generates_book_file(tmp_path) -> None:
    project = object.__new__(BookProject)
    project.paths = SimpleNamespace(project_dir=tmp_path, data_dir=tmp_path, output_dir=tmp_path / "output", figures_dir=tmp_path / ".data" / "figures")
    project.cfg = _workflow_app_config()
    project.cfg.quality.enabled = False
    project._write_checkpoint_path_override = None
    project._write_checkpoint_kind_override = None
    state = _state_with_sections()
    state.book_title = "测试书"
    state.current_phase = "completed"
    state.publication_approved = True
    _mark_book_ready_for_final_review(state)
    state.upsert_chapter_content(ChapterContent(chapter_id=1, title="第一章", markdown="# 第一章\n\n正文"))
    state.upsert_chapter_content(ChapterContent(chapter_id=2, title="第二章", markdown="# 第二章\n\n正文"))
    project._save_write_checkpoint("book-1", state)

    result = project.write_export("book-1", target="markdown")

    assert result["target"] == "markdown"
    assert result["book_markdown"] == str(tmp_path / "output" / "book.md")
    assert "word_file" not in result
    assert "# 第一章" in (tmp_path / "output" / "book.md").read_text(encoding="utf-8")


def test_write_export_all_generates_word_from_markdown(tmp_path, monkeypatch) -> None:
    project = object.__new__(BookProject)
    project.paths = SimpleNamespace(project_dir=tmp_path, data_dir=tmp_path, output_dir=tmp_path / "output", figures_dir=tmp_path / ".data" / "figures")
    project.cfg = _workflow_app_config()
    project.cfg.quality.enabled = False
    project._write_checkpoint_path_override = None
    project._write_checkpoint_kind_override = None
    state = _state_with_sections()
    state.current_phase = "completed"
    state.publication_approved = True
    _mark_book_ready_for_final_review(state)
    state.upsert_chapter_content(ChapterContent(chapter_id=1, title="第一章", markdown="# 第一章\n\n正文"))
    state.upsert_chapter_content(ChapterContent(chapter_id=2, title="第二章", markdown="# 第二章\n\n正文"))
    project._save_write_checkpoint("book-1", state)
    calls = []

    def fake_word(markdown_file, word_file, *, reference_docx=None, pandoc_bin="pandoc") -> str:
        calls.append((str(markdown_file), str(word_file), reference_docx, pandoc_bin))
        return str(word_file)

    monkeypatch.setattr("core.workflow.generate_word_output", fake_word)

    result = project.write_export("book-1", target="all")

    assert result["target"] == "all"
    assert result["word_file"] == str(tmp_path / "output" / "book.docx")
    assert calls == [(str(tmp_path / "output" / "book.md"), str(tmp_path / "output" / "book.docx"), None, "pandoc")]


def test_write_export_draft_uses_root_pdf_css(tmp_path, monkeypatch) -> None:
    project = object.__new__(BookProject)
    project.paths = SimpleNamespace(project_dir=tmp_path, data_dir=tmp_path, output_dir=tmp_path / "output", figures_dir=tmp_path / ".data" / "figures")
    project.cfg = _workflow_app_config()
    project.cfg.quality.enabled = False
    project._write_checkpoint_path_override = None
    project._write_checkpoint_kind_override = None
    state = _state_with_sections()
    state.current_phase = "completed"
    _mark_book_ready_for_final_review(state)
    state.upsert_chapter_content(ChapterContent(chapter_id=1, title="第一章", markdown="# 第一章\n\n正文"))
    project._save_write_checkpoint("book-1", state)
    css_file = tmp_path / "output" / "pdf_style.css"
    css_file.parent.mkdir(parents=True, exist_ok=True)
    css_file.write_text("@page { size: A4; }", encoding="utf-8")
    calls = []

    def fake_pdf(markdown_file, pdf_file, *, css_file=None, chrome_bin=None, pandoc_bin="pandoc", cover_html=None) -> str:
        calls.append((str(markdown_file), str(pdf_file), str(css_file)))
        return str(pdf_file)

    monkeypatch.setattr("core.workflow.generate_pdf_output", fake_pdf)

    result = project.write_export("book-1", target="pdf", draft=True)

    assert result["pdf_file"] == str(tmp_path / "output" / "draft" / "book.pdf")
    assert calls == [
        (
            str(tmp_path / "output" / "draft" / "book_clean.md"),
            str(tmp_path / "output" / "draft" / "book.pdf"),
            str(css_file),
        )
    ]
