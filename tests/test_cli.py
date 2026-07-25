from __future__ import annotations

from typer.testing import CliRunner

from cli import app
from core.state import BookState, ChapterContent, ChapterPlan, PartPlan, SectionContent, SectionPlan

runner = CliRunner()


def test_cli_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "kb" in result.output
    assert "outline" in result.output
    assert "write" in result.output
    assert "run" not in result.output
    assert "patch-chapter" not in result.output
    assert "status" not in result.output
    assert "contents" not in result.output
    assert "chapter" not in result.output
    assert "toc" not in result.output
    assert "show-chapter" not in result.output
    assert "ls" not in result.output
    assert "cat" not in result.output


def test_root_resume_flag_is_not_supported() -> None:
    result = runner.invoke(app, ["--resume", "--thread-id", "book-2"])

    assert result.exit_code != 0
    assert "No such option" in result.output or "no such option" in result.output.lower()


def test_write_status_uses_section_checkpoint_workflow(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def write_status(self, thread_id: str) -> dict[str, object]:
            calls.append(("write_status", thread_id))
            return {"thread_id": thread_id, "current_section": {"id": "1.1.1", "title": "小节"}}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["--thread-id", "book-2", "write", "status"])

    assert result.exit_code == 0
    assert '"id": "1.1.1"' in result.output
    assert calls == [("init", "config"), ("write_status", "book-2")]


def test_write_audit_command(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def write_audit(self, thread_id: str) -> dict[str, object]:
            calls.append(("write_audit", thread_id))
            return {
                "thread_id": thread_id,
                "checkpoint_exists": True,
                "lock": {"exists": True, "pid": 123, "operation": "write.resume", "started_at": "2026-07-11T12:00:00"},
                "worker_checkpoints": {"count": 1, "chapters": [{"chapter_id": 3}]},
                "progress": {
                    "phase": "completed",
                    "sections": {"reviewed": 3},
                    "chapters": {"approved": 1, "quality_failed": 1},
                    "section_contents": 3,
                    "chapter_contents": 2,
                    "total_words": 12345,
                },
                "manuscript_drift": {
                    "missing_section_files": [],
                    "missing_chapter_files": [],
                    "orphan_section_files": [],
                    "orphan_chapter_files": [],
                },
                "quality_failures": {
                    "failed_sections": [],
                    "failed_chapters": [2],
                    "section_issue_codes": {},
                    "chapter_issue_codes": {"fact.unsourced_hard_fact": 2},
                },
                "publication_audit": {
                    "pass": False,
                    "issue_count": 1,
                    "blocking_issue_count": 1,
                    "issues": [
                        {
                            "code": "chapter.quality_failed",
                            "severity": "blocker",
                            "chapter_id": 2,
                            "message": "第2章章节质量门未通过。",
                            "suggestion": "执行 write resume 2。",
                        }
                    ],
                },
                "recommended_commands": ["uv run python main.py write resume all"],
            }

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["--thread-id", "book-2", "write", "audit"])

    assert result.exit_code == 0
    assert "出版审计报告" in result.output
    assert "写作进程：🟡 运行中 pid=123 operation=write.resume" in result.output
    assert "章节未通过：第2章" in result.output
    assert "chapter.quality_failed" in result.output
    assert "uv run python main.py write resume all" in result.output
    assert calls == [("init", "config"), ("write_audit", "book-2")]


def test_write_audit_json_option(monkeypatch) -> None:
    class FakeProject:
        def __init__(self, config_path: str) -> None:
            pass

        def write_audit(self, thread_id: str) -> dict[str, object]:
            return {"thread_id": thread_id, "publication_audit": {"pass": False}}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["--thread-id", "book-2", "write", "audit", "--json"])

    assert result.exit_code == 0
    assert '"pass": false' in result.output


def test_kb_build_passes_rebuild_flag(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def kb_build(self, *, rebuild: bool = False, sparse_only: bool = False) -> dict[str, object]:
            calls.append(("kb_build", rebuild, sparse_only))
            return {"rebuild": rebuild, "sparse_only": sparse_only}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["kb", "build", "--rebuild"])

    assert result.exit_code == 0
    assert '"rebuild": true' in result.output
    assert calls == [("init", "config"), ("kb_build", True, False)]


def test_kb_build_passes_sparse_only_flag(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def kb_build(self, *, rebuild: bool = False, sparse_only: bool = False) -> dict[str, object]:
            calls.append(("kb_build", rebuild, sparse_only))
            return {"chunks": 12, "sparse_only": sparse_only}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["kb", "build", "--sparse-only"])

    assert result.exit_code == 0
    assert '"sparse_only": true' in result.output
    assert calls == [("init", "config"), ("kb_build", False, True)]


def test_write_resume_passes_human_target(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def write_resume(self, thread_id: str, *, target: str = "current") -> dict[str, object]:
            calls.append(("write_resume", thread_id, target))
            return {"thread_id": thread_id, "target": target, "sections_processed": 2}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["--thread-id", "book-2", "write", "resume", "1.1"])

    assert result.exit_code == 0
    assert '"target": "1.1"' in result.output
    assert calls == [("init", "config"), ("write_resume", "book-2", "1.1")]


def test_write_recover_manuscript_command(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def recover_manuscript(self, thread_id: str) -> dict[str, object]:
            calls.append(("recover_manuscript", thread_id))
            return {"sections_recovered": 2}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["write", "recover-manuscript"])

    assert result.exit_code == 0
    assert '"sections_recovered": 2' in result.output
    assert calls == [("init", "config"), ("recover_manuscript", "book-1")]


def test_write_manuscript_rebuild_chapters_command(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def rebuild_manuscript_chapters(self, thread_id: str, *, dry_run: bool = True) -> dict[str, object]:
            calls.append(("rebuild_manuscript_chapters", thread_id, dry_run))
            return {"chapters": 14, "secondary_headings": 79, "dry_run": dry_run}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(
        app,
        ["--thread-id", "book-2", "write", "manuscript", "rebuild-chapters", "--no-dry-run"],
    )

    assert result.exit_code == 0
    assert '"secondary_headings": 79' in result.output
    assert calls == [("init", "config"), ("rebuild_manuscript_chapters", "book-2", False)]


def test_write_figures_build_command(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def write_figures_build(self, thread_id: str, *, draft: bool = False, force: bool = False) -> dict[str, object]:
            calls.append(("write_figures_build", thread_id, draft, force))
            return {"generated_count": 2, "failed_count": 0, "draft": draft, "force": force}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["--thread-id", "book-2", "write", "figures", "build", "--draft", "--force"])

    assert result.exit_code == 0
    assert '"generated_count": 2' in result.output
    assert calls == [("init", "config"), ("write_figures_build", "book-2", True, True)]


def test_write_figures_upgrade_briefs_command(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def write_figures_upgrade_briefs(self, thread_id: str, *, dry_run: bool = False) -> dict[str, object]:
            calls.append(("write_figures_upgrade_briefs", thread_id, dry_run))
            return {"total": {"changed_blocks": 3}, "dry_run": dry_run}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["--thread-id", "book-2", "write", "figures", "upgrade-briefs", "--dry-run"])

    assert result.exit_code == 0
    assert '"changed_blocks": 3' in result.output
    assert calls == [("init", "config"), ("write_figures_upgrade_briefs", "book-2", True)]


def test_write_figures_audit_command(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def write_figures_audit(self, thread_id: str, *, draft: bool = False) -> dict[str, object]:
            calls.append(("write_figures_audit", thread_id, draft))
            return {"total": 2, "polished": 1, "draft": draft}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["--thread-id", "book-2", "write", "figures", "audit", "--draft"])

    assert result.exit_code == 0
    assert '"polished": 1' in result.output
    assert calls == [("init", "config"), ("write_figures_audit", "book-2", True)]


def test_write_figures_polish_plan_command(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def write_figures_polish_plan(self, thread_id: str) -> dict[str, object]:
            calls.append(("write_figures_polish_plan", thread_id))
            return {"total": 51, "pending": 51, "plan_path": "assets/figures/polished/polish-plan.json"}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["--thread-id", "book-2", "write", "figures", "polish-plan"])

    assert result.exit_code == 0
    assert '"pending": 51' in result.output
    assert calls == [("init", "config"), ("write_figures_polish_plan", "book-2")]


def test_write_references_audit_command(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def write_references_audit(self, thread_id: str) -> dict[str, object]:
            calls.append(("write_references_audit", thread_id))
            return {"marker_count": 3, "missing_count": 0}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["--thread-id", "book-2", "write", "references", "audit"])

    assert result.exit_code == 0
    assert '"marker_count": 3' in result.output
    assert calls == [("init", "config"), ("write_references_audit", "book-2")]


def test_write_references_clean_command(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def write_references_clean(self, thread_id: str, *, mode: str) -> dict[str, object]:
            calls.append(("write_references_clean", thread_id, mode))
            return {"mode": mode, "changed_count": 2}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["--thread-id", "book-2", "write", "references", "clean", "--mode", "endnote"])

    assert result.exit_code == 0
    assert '"mode": "endnote"' in result.output
    assert calls == [("init", "config"), ("write_references_clean", "book-2", "endnote")]


def test_write_export_command_passes_target(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def write_export(self, thread_id: str, *, target: str = "all", draft: bool = False) -> dict[str, object]:
            calls.append(("write_export", thread_id, target, draft))
            return {"target": target, "draft": draft, "output_dir": "output", "book_markdown": "output/book.md"}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["--thread-id", "book-2", "write", "export", "markdown"])

    assert result.exit_code == 0
    assert '"target": "markdown"' in result.output
    assert calls == [("init", "config"), ("write_export", "book-2", "markdown", False)]


def test_write_export_defaults_to_all(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def write_export(self, thread_id: str, *, target: str = "all", draft: bool = False) -> dict[str, object]:
            calls.append(("write_export", thread_id, target, draft))
            return {
                "target": target,
                "draft": draft,
                "output_dir": "output",
                "book_markdown": "output/book.md",
                "word_file": "output/book.docx",
            }

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["write", "export"])

    assert result.exit_code == 0
    assert '"target": "all"' in result.output
    assert calls == [("init", "config"), ("write_export", "book-1", "all", False)]


def test_write_export_draft_option(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def write_export(self, thread_id: str, *, target: str = "all", draft: bool = False) -> dict[str, object]:
            calls.append(("write_export", thread_id, target, draft))
            return {
                "target": target,
                "draft": draft,
                "output_dir": "output/draft",
                "book_markdown": "output/draft/book.md",
            }

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["write", "export", "markdown", "--draft"])

    assert result.exit_code == 0
    assert '"draft": true' in result.output
    assert calls == [("init", "config"), ("write_export", "book-1", "markdown", True)]


def test_write_export_output_command_is_removed() -> None:
    result = runner.invoke(app, ["write", "export-output"])

    assert result.exit_code != 0
    assert "No such command" in result.output or "No such command" in result.stderr


def test_write_resume_max_sections_option_is_removed() -> None:
    result = runner.invoke(app, ["write", "resume", "--max-sections", "1"])

    assert result.exit_code != 0
    assert "No such option" in result.output or "no such option" in result.output.lower()


def test_write_section_prints_second_level_prefix(monkeypatch) -> None:
    state = BookState(
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
                    )
                ],
            )
        ],
        section_contents=[
            SectionContent(section_id="1.1.1", chapter_id=1, title="一", markdown="### 1.1.1 一\n\n正文一"),
            SectionContent(section_id="1.1.2", chapter_id=1, title="二", markdown="### 1.1.2 二\n\n正文二"),
            SectionContent(section_id="1.2.1", chapter_id=1, title="三", markdown="### 1.2.1 三\n\n正文三"),
        ],
    )

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            pass

        def load_write_checkpoint_with_workers(self, thread_id: str) -> BookState:
            return state

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["write", "section", "1.1"])

    assert result.exit_code == 0
    assert "正文一" in result.output
    assert "正文二" in result.output
    assert "scope: section" in result.output
    assert "正文三" not in result.output


def test_write_section_prints_partial_chapter(monkeypatch) -> None:
    state = BookState(
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
                        ],
                    )
                ],
            )
        ],
        section_contents=[
            SectionContent(section_id="1.1.1", chapter_id=1, title="一", markdown="### 1.1.1 一\n\n正文一"),
            SectionContent(section_id="1.1.2", chapter_id=1, title="二", markdown="### 1.1.2 二\n\n正文二"),
        ],
    )

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            pass

        def load_write_checkpoint_with_workers(self, thread_id: str) -> BookState:
            return state

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["write", "section", "1"])

    assert result.exit_code == 0
    assert "# 第1章 第一章" in result.output
    assert "正文一" in result.output
    assert "正文二" in result.output
    assert "scope: chapter" in result.output
    assert "section-status" in result.output


def test_write_section_prints_failure_status_for_existing_chapter(monkeypatch) -> None:
    state = BookState(
        parts=[
            PartPlan(
                name="基础篇",
                prefix="一",
                chapters=[
                    ChapterPlan(
                        id=1,
                        title="第一章",
                        status="quality_failed",
                        sections=[
                            SectionPlan(
                                id="1.1.1",
                                chapter_id=1,
                                title="一",
                                heading="1.1.1 一",
                                status="review_failed",
                            )
                        ],
                    )
                ],
            )
        ],
        section_contents=[
            SectionContent(
                section_id="1.1.1",
                chapter_id=1,
                title="一",
                markdown="### 1.1.1 一\n\n正文一",
                revision_feedback="缺少 book-figure",
            )
        ],
        chapters=[
            ChapterContent(
                chapter_id=1,
                title="第一章",
                markdown="# 第1章 第一章\n\n正文一",
                publication_feedback="章节质量门未通过",
            )
        ],
    )

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            pass

        def load_write_checkpoint_with_workers(self, thread_id: str) -> BookState:
            return state

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["write", "section", "1"])

    assert result.exit_code == 0
    assert "status: quality_failed" in result.output
    assert "1.1.1: review_failed" in result.output
    assert "缺少 book-figure" in result.output


def test_write_contents_prints_section_checkpoint_outline(monkeypatch) -> None:
    state = BookState(
        current_phase="writing",
        current_section_id="1.1.2",
        parts=[
            PartPlan(
                name="基础篇",
                prefix="一",
                chapters=[
                    ChapterPlan(
                        id=1,
                        title="第一章",
                        sections=[
                            SectionPlan(
                                id="1.1.1",
                                chapter_id=1,
                                title="小节一",
                                heading="1.1.1 小节一",
                                parent_title="第一节",
                            ),
                            SectionPlan(
                                id="1.1.2",
                                chapter_id=1,
                                title="小节二",
                                heading="1.1.2 小节二",
                                parent_title="第一节",
                            ),
                            SectionPlan(
                                id="1.2.1",
                                chapter_id=1,
                                title="小节三",
                                heading="1.2.1 小节三",
                                parent_title="第二节",
                            ),
                        ],
                    ),
                    ChapterPlan(
                        id=2,
                        title="第二章",
                        sections=[
                            SectionPlan(
                                id="2.1.1",
                                chapter_id=2,
                                title="小节四",
                                heading="2.1.1 小节四",
                                parent_title="第三节",
                            )
                        ],
                    ),
                ],
            )
        ],
        section_contents=[
            SectionContent(section_id="1.1.1", chapter_id=1, title="小节一", markdown="### 1.1.1 小节一\n\n正文")
        ],
    )

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            pass

        def load_write_checkpoint_with_workers(self, thread_id: str) -> BookState:
            return state

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["write", "contents"])

    assert result.exit_code == 0
    assert result.stdout.startswith("目录进度\n")
    assert "小节审校：✅ 通过｜❌ 未通过｜🟡 待审校｜⬜ 待写作" in result.stdout
    assert "章节质量门：✅ 通过｜❌ 未通过｜🟡 审核中｜⬜ 待合稿｜📘 已合稿" in result.stdout
    assert "小节审校：已写 1/4｜✅ 通过 0｜❌ 未通过 0｜🟡 待审校 1｜⬜ 待写作 3" in result.stdout
    assert "章节质量门：已合稿 0/2｜✅ 通过 0｜❌ 未通过 0｜🟡 审核中 0｜⬜ 待合稿 2" in result.stdout
    assert "一、基础篇" in result.stdout
    assert "第1章 第一章" in result.stdout
    assert "章节质量门：⬜ 待合稿｜合稿：⬜ 未合稿｜小节：1/3" in result.stdout
    assert "1.1 第一节" in result.stdout
    assert "小节审校：🟡 待审校｜1.1.1 小节一" in result.stdout
    assert "小节审校：⬜ 待写作｜1.1.2 小节二 ← 当前" in result.stdout
    assert "1.2 第二节" in result.stdout
    assert "第2章 第二章" in result.stdout
    assert "章节质量门：⬜ 待合稿｜合稿：⬜ 未合稿｜小节：0/1" in result.stdout


def test_write_contents_distinguishes_review_and_quality_status(monkeypatch) -> None:
    state = BookState(
        current_phase="writing",
        parts=[
            PartPlan(
                name="基础篇",
                prefix="一",
                chapters=[
                    ChapterPlan(
                        id=1,
                        title="第一章",
                        status="quality_failed",
                        sections=[
                            SectionPlan(
                                id="1.1.1",
                                chapter_id=1,
                                title="小节一",
                                heading="1.1.1 小节一",
                                parent_title="第一节",
                                status="reviewed",
                            ),
                            SectionPlan(
                                id="1.1.2",
                                chapter_id=1,
                                title="小节二",
                                heading="1.1.2 小节二",
                                parent_title="第一节",
                                status="review_failed",
                            ),
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
                                title="小节三",
                                heading="2.1.1 小节三",
                                parent_title="第二节",
                                status="reviewed",
                            )
                        ],
                    ),
                ],
            )
        ],
        section_contents=[
            SectionContent(section_id="1.1.1", chapter_id=1, title="小节一", markdown="正文"),
            SectionContent(
                section_id="1.1.2",
                chapter_id=1,
                title="小节二",
                markdown="正文",
                revision_feedback="缺少 book-figure",
            ),
            SectionContent(section_id="2.1.1", chapter_id=2, title="小节三", markdown="正文"),
        ],
        chapters=[
            ChapterContent(
                chapter_id=1,
                title="第一章",
                markdown="正文",
                publication_feedback=(
                    '{"pass": false, "issues": [{"code": "asset.invalid_book_figure", "message": "图表规格块不完整"}]}'
                ),
                fact_feedback=(
                    '{"pass": false, "issues": [{"code": "fact.unsourced_statistics", "message": "统计数据缺少来源"}]}'
                ),
            ),
            ChapterContent(chapter_id=2, title="第二章", markdown="正文"),
        ],
    )

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            pass

        def load_write_checkpoint_with_workers(self, thread_id: str) -> BookState:
            return state

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["write", "contents"])

    assert result.exit_code == 0
    assert "章节质量门：已合稿 2/2｜✅ 通过 1｜❌ 未通过 1｜🟡 审核中 0｜⬜ 待合稿 0" in result.stdout
    assert "章节质量门：❌ 未通过｜合稿：📘 已合稿｜小节：2/2" in result.stdout
    assert "质量原因：asset.invalid_book_figure：图表规格块不完整" in result.stdout
    assert "fact.unsourced_statistics：统计数据缺少来源" in result.stdout
    assert "小节审校：✅ 通过｜1.1.1 小节一" in result.stdout
    assert "小节审校：❌ 未通过｜1.1.2 小节二｜原因：缺少 book-figure" in result.stdout
    assert "章节质量门：✅ 通过｜合稿：📘 已合稿｜小节：1/1" in result.stdout


def test_root_contents_command_is_removed() -> None:
    result = runner.invoke(app, ["contents"])

    assert result.exit_code != 0
    assert "No such command" in result.output or "No such command" in result.stderr


def test_removed_root_commands_are_unavailable() -> None:
    removed_commands = [
        "run",
        "resume",
        "status",
        "chapter",
        "export-state",
        "patch-chapter",
        "revise-chapter",
        "regenerate-output",
        "reset",
    ]
    for command in removed_commands:
        result = runner.invoke(app, [command])

        assert result.exit_code != 0
        assert "No such command" in result.output or "No such command" in result.stderr
