"""Dashboard 查询与命令服务。"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from itertools import pairwise
from pathlib import Path
from threading import Lock, Thread
from typing import TYPE_CHECKING, Any, cast

from api.log_reader import LogEntry, read_logs
from core.config import get_config_paths, load_app_config
from core.log import DEFAULT_LOG_FILE
from core.state import BookState, ChapterContent
from graph import BookWriterGraph

if TYPE_CHECKING:
    from collections.abc import Callable


class PathTraversalError(ValueError):
    """输出文件路径越界。"""


class DashboardService:
    def __init__(
        self,
        *,
        config_dir: str = "config",
        thread_id: str = "book-1",
        graph_factory: Callable[[str], Any] | None = None,
        state_loader: Callable[[str], BookState | None] | None = None,
        output_dir: str | Path | None = None,
        log_file: str | Path | None = None,
    ) -> None:
        self.config_dir = config_dir
        self.thread_id = thread_id
        self._graph_factory = graph_factory or BookWriterGraph
        self._state_loader = state_loader
        self._graph: Any | None = None
        self._running_threads: set[str] = set()
        self._lock = Lock()
        self.output_dir = Path(output_dir) if output_dir is not None else Path("output")
        self.log_file = Path(log_file) if log_file is not None else Path(DEFAULT_LOG_FILE)

    @property
    def graph(self) -> Any:
        if self._graph is None:
            self._graph = self._graph_factory(self.config_dir)
            if self.output_dir == Path("output"):
                app_config = load_app_config(self.config_dir)
                self.output_dir = get_config_paths(app_config).output_dir
        return self._graph

    def get_state(self, thread_id: str | None = None) -> BookState | None:
        selected_thread_id = thread_id or self.thread_id
        if self._state_loader:
            return self._state_loader(selected_thread_id)
        return cast("BookState | None", self.graph.get_book_state(selected_thread_id))

    def get_status(self, thread_id: str | None = None) -> dict[str, Any]:
        selected_thread_id = thread_id or self.thread_id
        status = dict(self.graph.get_status(selected_thread_id))
        state = self.get_state(selected_thread_id)
        total_chapters = len(state.get_all_chapters_flat()) if state else 0
        chapters_written = int(status.get("chapters_written") or 0)
        status["total_chapters"] = total_chapters
        status["progress"] = chapters_written / total_chapters if total_chapters else 0.0
        return status

    def get_chapters(self, thread_id: str | None = None) -> dict[str, Any]:
        state = self.get_state(thread_id)
        if state is None:
            return {"book_title": "", "parts": []}
        return {
            "book_title": state.book_title,
            "parts": [
                {
                    "name": part.name,
                    "prefix": part.prefix,
                    "chapters": [self._chapter_summary(state, chapter.id, chapter.title, chapter.status) for chapter in part.chapters],
                }
                for part in state.parts
            ],
        }

    def get_chapter(self, chapter_id: int, thread_id: str | None = None) -> dict[str, Any]:
        state = self.get_state(thread_id)
        if state is None:
            return {}
        plan = next((chapter for chapter in state.get_all_chapters_flat() if chapter.id == chapter_id), None)
        content = state.get_chapter_content(chapter_id)
        return {
            "id": chapter_id,
            "title": content.title if content else (plan.title if plan else ""),
            "status": plan.status if plan else "pending",
            "markdown": content.markdown if content else "",
            "word_count": _word_count(content),
            "feedback": _feedback(content),
            "revision_count": content.revision_count if content else 0,
        }

    def get_output_files(self) -> list[dict[str, Any]]:
        root = self.output_dir.resolve()
        if not root.exists():
            return []
        files: list[dict[str, Any]] = []
        for path in sorted(root.rglob("*")):
            if path.is_file():
                files.append({"path": str(path.relative_to(root)), "size": path.stat().st_size})
        return files

    def read_output_file(self, relative_path: str) -> str:
        root = self.output_dir.resolve()
        path = (root / relative_path).resolve()
        if root != path and root not in path.parents:
            raise PathTraversalError(f"输出路径越界: {relative_path}")
        if not path.is_file():
            raise FileNotFoundError(relative_path)
        return path.read_text(encoding="utf-8")

    def get_logs(
        self,
        *,
        level: str | None = None,
        agent: str | None = None,
        chapter: int | None = None,
        limit: int = 200,
    ) -> list[LogEntry]:
        return read_logs(self.log_file, level=level, agent=agent, chapter=chapter, limit=limit)

    def get_metrics(self) -> dict[str, Any]:
        entries = self.get_logs(limit=1000)
        agent_durations: dict[str, int] = defaultdict(int)
        chapter_durations: dict[str, int] = defaultdict(int)
        for current, next_entry in pairwise(entries):
            if not current.timestamp or not next_entry.timestamp or not current.agent:
                continue
            duration = _seconds_between(current.timestamp, next_entry.timestamp)
            if duration <= 0 or duration > 3600:
                continue
            agent_durations[current.agent] += duration
            if current.chapter_id is not None:
                chapter_durations[str(current.chapter_id)] += duration
        return {
            "agent_durations": dict(agent_durations),
            "chapter_durations": dict(chapter_durations),
            "log_entries": len(entries),
        }

    def get_rag_status(self, thread_id: str | None = None) -> dict[str, Any]:
        return dict(self.get_status(thread_id).get("rag") or {})

    def start_run(self, thread_id: str, *, fresh: bool = False) -> dict[str, Any]:
        return self._start_background(thread_id, lambda: self.graph.run(thread_id=thread_id, fresh=fresh))

    def resume(self, thread_id: str) -> dict[str, Any]:
        return self._start_background(thread_id, lambda: self.graph.resume(thread_id=thread_id))

    def regenerate_output(self, thread_id: str) -> dict[str, Any]:
        return {"output_dir": self.graph.regenerate_output(thread_id), "thread_id": thread_id}

    def patch_chapter(
        self,
        thread_id: str,
        chapter_id: int,
        markdown: str,
        *,
        regenerate_output: bool = False,
    ) -> dict[str, Any]:
        self.graph.patch_chapter(thread_id, chapter_id, markdown)
        output_dir = self.graph.regenerate_output(thread_id) if regenerate_output else ""
        return {"patched": True, "chapter_id": chapter_id, "output_dir": output_dir}

    def revise_chapter(
        self,
        thread_id: str,
        chapter_id: int,
        feedback: str,
        *,
        regenerate_output: bool = False,
    ) -> dict[str, Any]:
        self.graph.revise_chapter(thread_id, chapter_id, feedback)
        output_dir = self.graph.regenerate_output(thread_id) if regenerate_output else ""
        return {"revised": True, "chapter_id": chapter_id, "output_dir": output_dir}

    def reset_thread(self, thread_id: str, *, confirm: str) -> dict[str, Any]:
        expected = f"RESET {thread_id}"
        if confirm != expected:
            raise ValueError(f"reset 需要确认字段: {expected}")
        self.graph.reset_thread(thread_id)
        return {"reset": True, "thread_id": thread_id}

    def _start_background(self, thread_id: str, action: Callable[[], object]) -> dict[str, Any]:
        with self._lock:
            if thread_id in self._running_threads:
                return {"accepted": False, "running": True, "thread_id": thread_id}
            self._running_threads.add(thread_id)

        def run_action() -> None:
            try:
                action()
            finally:
                with self._lock:
                    self._running_threads.discard(thread_id)

        Thread(target=run_action, daemon=True).start()
        return {"accepted": True, "running": True, "thread_id": thread_id}

    def _chapter_summary(self, state: BookState, chapter_id: int, title: str, status: str) -> dict[str, Any]:
        content = state.get_chapter_content(chapter_id)
        return {
            "id": chapter_id,
            "title": title,
            "status": status,
            "written": bool(content and content.markdown.strip()),
            "word_count": _word_count(content),
            "feedback": _feedback(content),
            "revision_count": content.revision_count if content else 0,
        }


def _word_count(content: ChapterContent | None) -> int:
    if content is None:
        return 0
    return content.word_count or len(content.markdown)


def _feedback(content: ChapterContent | None) -> dict[str, str]:
    if content is None:
        return {"fact": "", "style": "", "review": ""}
    return {"fact": content.fact_feedback, "style": content.style_feedback, "review": content.review_feedback}


def _seconds_between(start: str, end: str) -> int:
    start_time = dt.datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
    end_time = dt.datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
    return int((end_time - start_time).total_seconds())
