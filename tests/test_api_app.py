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
