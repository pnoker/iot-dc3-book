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
            return {"thread_id": thread_id, "publication_audit": {"pass": False}}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["--thread-id", "book-2", "write", "audit"])

    assert result.exit_code == 0
    assert '"pass": false' in result.output
    assert calls == [("init", "config"), ("write_audit", "book-2")]


def test_kb_build_passes_rebuild_flag(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def kb_build(self, *, rebuild: bool = False) -> dict[str, object]:
            calls.append(("kb_build", rebuild))
            return {"rebuild": rebuild}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["kb", "build", "--rebuild"])

    assert result.exit_code == 0
    assert '"rebuild": true' in result.output
    assert calls == [("init", "config"), ("kb_build", True)]


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


def test_write_export_command_passes_target(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def write_export(self, thread_id: str, *, target: str = "all") -> dict[str, object]:
            calls.append(("write_export", thread_id, target))
            return {"target": target, "output_dir": "output", "book_markdown": "output/book.md"}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["--thread-id", "book-2", "write", "export", "markdown"])

    assert result.exit_code == 0
    assert '"target": "markdown"' in result.output
    assert calls == [("init", "config"), ("write_export", "book-2", "markdown")]


def test_write_export_defaults_to_all(monkeypatch) -> None:
    calls = []

    class FakeProject:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def write_export(self, thread_id: str, *, target: str = "all") -> dict[str, object]:
            calls.append(("write_export", thread_id, target))
            return {"target": target, "output_dir": "output", "book_markdown": "output/book.md", "word_file": "output/book.docx"}

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["write", "export"])

    assert result.exit_code == 0
    assert '"target": "all"' in result.output
    assert calls == [("init", "config"), ("write_export", "book-1", "all")]


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

        def load_write_checkpoint(self, thread_id: str) -> BookState:
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

        def load_write_checkpoint(self, thread_id: str) -> BookState:
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

        def load_write_checkpoint(self, thread_id: str) -> BookState:
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

        def load_write_checkpoint(self, thread_id: str) -> BookState:
            return state

    monkeypatch.setattr("cli.BookProject", FakeProject)
    result = runner.invoke(app, ["write", "contents"])

    assert result.exit_code == 0
    assert result.stdout.startswith("目录\n")
    assert "一、基础篇" in result.stdout
    assert "第1章 第一章（1/3，未合稿，待写作）" in result.stdout
    assert "1.1 第一节" in result.stdout
    assert "[✓] 1.1.1 小节一（待写作）" in result.stdout
    assert "[ ] 1.1.2 小节二（待写作） ← 当前" in result.stdout
    assert "1.2 第二节" in result.stdout
    assert "第2章 第二章（0/1，未合稿，待写作）" in result.stdout


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
