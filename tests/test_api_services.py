from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from api.services import DashboardService, PathTraversalError
from core.state import BookState, ChapterContent, ChapterPlan, PartPlan

if TYPE_CHECKING:
    from pathlib import Path


class FakeGraph:
    def get_status(self, thread_id: str) -> dict[str, object]:
        assert thread_id == "book-1"
        return {
            "thread_id": "book-1",
            "has_checkpoint": True,
            "phase": "writing",
            "complete": False,
            "next_nodes": ["style_check"],
            "current_chapter": {"id": 2, "title": "体系架构"},
            "chapters_written": 1,
            "rag": {"chunk_count": 10, "healthy": True},
        }


def make_state() -> BookState:
    return BookState(
        book_title="物联网技术与实践",
        parts=[
            PartPlan(
                name="基础篇",
                prefix="一",
                chapters=[
                    ChapterPlan(id=1, title="概述", summary="概述章", status="approved"),
                    ChapterPlan(id=2, title="体系架构", summary="架构章", status="written"),
                ],
            )
        ],
        chapters=[
            ChapterContent(
                chapter_id=1,
                title="概述",
                markdown="# 第一章\n正文内容",
                fact_feedback="事实 OK",
                style_feedback="风格 OK",
                review_feedback="审校 OK",
            )
        ],
        current_phase="writing",
        current_part_idx=0,
        current_chapter_idx=1,
    )


def test_get_dashboard_status_adds_total_chapters() -> None:
    service = DashboardService(graph_factory=lambda config: FakeGraph(), state_loader=lambda thread_id: make_state())

    status = service.get_status("book-1")

    assert status["thread_id"] == "book-1"
    assert status["total_chapters"] == 2
    assert status["chapters_written"] == 1
    assert status["progress"] == pytest.approx(0.5)


def test_get_chapters_returns_tree_with_feedback_summary() -> None:
    service = DashboardService(graph_factory=lambda config: FakeGraph(), state_loader=lambda thread_id: make_state())

    tree = service.get_chapters("book-1")

    assert tree["book_title"] == "物联网技术与实践"
    assert tree["parts"][0]["name"] == "基础篇"
    first = tree["parts"][0]["chapters"][0]
    second = tree["parts"][0]["chapters"][1]
    assert first["written"] is True
    assert first["word_count"] == len("# 第一章\n正文内容")
    assert first["feedback"] == {"fact": "事实 OK", "style": "风格 OK", "review": "审校 OK"}
    assert second["written"] is False


def test_read_output_file_rejects_path_traversal(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "chapter.md").write_text("# 正文", encoding="utf-8")
    service = DashboardService(output_dir=output_dir)

    assert service.read_output_file("chapter.md") == "# 正文"
    with pytest.raises(PathTraversalError):
        service.read_output_file("../.env")


def test_get_metrics_aggregates_log_durations(tmp_path: Path) -> None:
    log_file = tmp_path / "book-writer.log"
    log_file.write_text(
        "\n".join(
            [
                "2026-07-02 17:05:25 | INFO    | book_writer.WriterAgent | 撰写第2章 物联网体系架构...",
                "2026-07-02 17:07:09 | INFO    | book_writer.FactCheckerAgent | 事实核查第2章...",
                "2026-07-02 17:07:39 | INFO    | book_writer.WriterAgent | 修改第2章...",
            ]
        ),
        encoding="utf-8",
    )
    service = DashboardService(log_file=log_file)

    metrics = service.get_metrics()

    assert metrics["agent_durations"]["WriterAgent"] == 104
    assert metrics["agent_durations"]["FactCheckerAgent"] == 30
    assert metrics["chapter_durations"]["2"] == 134


def test_start_run_uses_thread_lock(monkeypatch) -> None:
    calls: list[tuple[str, str, bool]] = []

    class SlowFakeGraph:
        def run(self, thread_id: str, fresh: bool = False) -> dict[str, object]:
            calls.append(("run", thread_id, fresh))
            return {"ok": True}

    service = DashboardService(graph_factory=lambda config: SlowFakeGraph())
    monkeypatch.setattr("api.services.Thread", InlineThread)

    first = service.start_run("book-1", fresh=True)
    second = service.start_run("book-1", fresh=False)

    assert first == {"accepted": True, "running": True, "thread_id": "book-1"}
    assert second == {"accepted": True, "running": True, "thread_id": "book-1"}
    assert calls == [("run", "book-1", True), ("run", "book-1", False)]


def test_reset_requires_exact_confirmation() -> None:
    calls: list[tuple[str, str]] = []

    class FakeResetGraph:
        def reset_thread(self, thread_id: str) -> None:
            calls.append(("reset", thread_id))

    service = DashboardService(graph_factory=lambda config: FakeResetGraph())

    with pytest.raises(ValueError, match="RESET book-1"):
        service.reset_thread("book-1", confirm="yes")

    assert service.reset_thread("book-1", confirm="RESET book-1") == {"reset": True, "thread_id": "book-1"}
    assert calls == [("reset", "book-1")]


def test_patch_chapter_delegates_to_graph_and_optionally_regenerates() -> None:
    calls: list[tuple[str, object]] = []

    class FakePatchGraph:
        def patch_chapter(self, thread_id: str, chapter_id: int, markdown: str) -> None:
            calls.append(("patch", thread_id, chapter_id, markdown))

        def regenerate_output(self, thread_id: str) -> str:
            calls.append(("output", thread_id))
            return "output"

    service = DashboardService(graph_factory=lambda config: FakePatchGraph())

    result = service.patch_chapter("book-1", 7, "# 第七章", regenerate_output=True)

    assert result == {"patched": True, "chapter_id": 7, "output_dir": "output"}
    assert calls == [("patch", "book-1", 7, "# 第七章"), ("output", "book-1")]


class InlineThread:
    def __init__(self, target: object, daemon: bool) -> None:
        self._target = target
        self.daemon = daemon

    def start(self) -> None:
        self._target()
