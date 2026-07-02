from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from api.app import create_app

if TYPE_CHECKING:
    from pathlib import Path


class FakeService:
    def get_status(self, thread_id: str | None = None) -> dict[str, object]:
        return {"thread_id": thread_id or "book-1", "phase": "writing", "progress": 0.5}

    def get_chapters(self, thread_id: str | None = None) -> dict[str, object]:
        return {"book_title": "物联网技术与实践", "parts": []}

    def get_chapter(self, chapter_id: int, thread_id: str | None = None) -> dict[str, object]:
        return {"id": chapter_id, "title": "概述", "markdown": "# 概述"}

    def get_logs(self, **kwargs: object) -> list[object]:
        return []

    def get_output_files(self) -> list[dict[str, object]]:
        return [{"path": "00-封面.md", "size": 10}]

    def read_output_file(self, relative_path: str) -> str:
        return "# 封面"

    def get_metrics(self) -> dict[str, object]:
        return {"agent_durations": {"WriterAgent": 100}, "chapter_durations": {"1": 100}}

    def get_rag_status(self, thread_id: str | None = None) -> dict[str, object]:
        return {"chunk_count": 10, "healthy": True}


def test_status_route_returns_dashboard_status() -> None:
    client = TestClient(create_app(service=FakeService()))

    response = client.get("/api/status?thread_id=book-2")

    assert response.status_code == 200
    assert response.json()["thread_id"] == "book-2"
    assert response.json()["phase"] == "writing"


def test_output_file_route_returns_markdown() -> None:
    client = TestClient(create_app(service=FakeService()))

    response = client.get("/api/output/file", params={"path": "00-封面.md"})

    assert response.status_code == 200
    assert response.json() == {"path": "00-封面.md", "content": "# 封面"}


def test_static_web_assets_are_served_when_present(tmp_path: Path) -> None:
    web_dist = tmp_path / "dist"
    web_dist.mkdir()
    (web_dist / "index.html").write_text("<div id='app'></div>", encoding="utf-8")
    client = TestClient(create_app(service=FakeService(), web_dist=web_dist))

    response = client.get("/")

    assert response.status_code == 200
    assert "app" in response.text


class FakeCommandService(FakeService):
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def start_run(self, thread_id: str, *, fresh: bool = False) -> dict[str, object]:
        self.calls.append(("run", thread_id, fresh))
        return {"accepted": True, "running": True, "thread_id": thread_id}

    def resume(self, thread_id: str) -> dict[str, object]:
        self.calls.append(("resume", thread_id))
        return {"accepted": True, "running": True, "thread_id": thread_id}

    def regenerate_output(self, thread_id: str) -> dict[str, object]:
        self.calls.append(("output", thread_id))
        return {"output_dir": "output"}

    def patch_chapter(self, thread_id: str, chapter_id: int, markdown: str, *, regenerate_output: bool = False) -> dict[str, object]:
        self.calls.append(("patch", thread_id, chapter_id, markdown, regenerate_output))
        return {"patched": True, "chapter_id": chapter_id}

    def revise_chapter(self, thread_id: str, chapter_id: int, feedback: str, *, regenerate_output: bool = False) -> dict[str, object]:
        self.calls.append(("revise", thread_id, chapter_id, feedback, regenerate_output))
        return {"revised": True, "chapter_id": chapter_id}

    def reset_thread(self, thread_id: str, *, confirm: str) -> dict[str, object]:
        self.calls.append(("reset", thread_id, confirm))
        return {"reset": True, "thread_id": thread_id}


def test_command_routes_delegate_to_service() -> None:
    service = FakeCommandService()
    client = TestClient(create_app(service=service))

    assert client.post("/api/run", json={"thread_id": "book-1", "fresh": True}).json()["accepted"] is True
    assert client.post("/api/resume", json={"thread_id": "book-1"}).json()["accepted"] is True
    assert client.post("/api/regenerate-output", json={"thread_id": "book-1"}).json()["output_dir"] == "output"
    assert client.post("/api/chapters/7/patch", json={"thread_id": "book-1", "markdown": "# 七", "regenerate_output": True}).json()["patched"] is True
    assert client.post("/api/chapters/7/revise", json={"thread_id": "book-1", "feedback": "加强案例"}).json()["revised"] is True
    assert client.post("/api/reset", json={"thread_id": "book-1", "confirm": "RESET book-1"}).json()["reset"] is True

    assert service.calls == [
        ("run", "book-1", True),
        ("resume", "book-1"),
        ("output", "book-1"),
        ("patch", "book-1", 7, "# 七", True),
        ("revise", "book-1", 7, "加强案例", False),
        ("reset", "book-1", "RESET book-1"),
    ]
