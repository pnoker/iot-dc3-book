from __future__ import annotations

from typer.testing import CliRunner

from cli import app

runner = CliRunner()


def test_cli_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "run" in result.output
    assert "patch-chapter" in result.output
    assert "dashboard" in result.output


def test_dashboard_command_starts_uvicorn(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    def fake_run(app_path: str, **kwargs: object) -> None:
        calls.append((app_path, kwargs))

    monkeypatch.setattr("cli.uvicorn.run", fake_run)

    result = runner.invoke(app, ["dashboard", "--host", "127.0.0.1", "--port", "18080"])

    assert result.exit_code == 0
    assert calls == [("api.app:app", {"host": "127.0.0.1", "port": 18080, "reload": False})]


def test_legacy_resume_flag_is_not_supported() -> None:
    result = runner.invoke(app, ["--resume", "--thread-id", "book-2"])

    assert result.exit_code != 0
    assert "No such option" in result.output or "no such option" in result.output.lower()


def test_status_command_accepts_thread_id_without_executing(monkeypatch) -> None:
    calls = []

    class FakeWriter:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def get_status(self, thread_id: str) -> dict[str, object]:
            calls.append(("status", thread_id))
            return {"thread_id": thread_id}

    monkeypatch.setattr("cli.BookWriterGraph", FakeWriter)
    result = runner.invoke(app, ["--thread-id", "book-2", "status"])

    assert result.exit_code == 0
    assert '"thread_id": "book-2"' in result.output
    assert calls == [("init", "config"), ("status", "book-2")]


def test_patch_chapter_reads_markdown_and_regenerates_output(tmp_path, monkeypatch) -> None:
    markdown_file = tmp_path / "chapter.md"
    markdown_file.write_text("# chapter", encoding="utf-8")
    calls = []

    class FakeWriter:
        def __init__(self, config_path: str) -> None:
            calls.append(("init", config_path))

        def patch_chapter(self, thread_id: str, chapter_id: int, markdown: str) -> None:
            calls.append(("patch", thread_id, chapter_id, markdown))

        def regenerate_output(self, thread_id: str) -> str:
            calls.append(("output", thread_id))
            return "output"

    monkeypatch.setattr("cli.BookWriterGraph", FakeWriter)
    result = runner.invoke(app, ["patch-chapter", "--chapter-id", "7", "--file", str(markdown_file), "--regenerate-output"])

    assert result.exit_code == 0
    assert calls == [("init", "config"), ("patch", "book-1", 7, "# chapter"), ("output", "book-1")]
