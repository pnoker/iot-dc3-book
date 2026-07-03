"""FastAPI Dashboard 应用。"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.log_reader import LogEntry
from api.models import PatchChapterCommand, ResetCommand, ReviseChapterCommand, RunCommand, ThreadCommand
from api.services import DashboardService, PathTraversalError


def create_app(*, service: DashboardService | Any | None = None, web_dist: str | Path | None = None) -> FastAPI:
    dashboard_service = service or DashboardService()
    app = FastAPI(title="mi-book-writer Dashboard", version="0.1.0")

    @app.get("/api/status")
    def get_status(thread_id: str = "book-1") -> dict[str, Any]:
        return dashboard_service.get_status(thread_id)

    @app.get("/api/chapters")
    def get_chapters(thread_id: str = "book-1") -> dict[str, Any]:
        return dashboard_service.get_chapters(thread_id)

    @app.get("/api/chapters/{chapter_id}")
    def get_chapter(chapter_id: int, thread_id: str = "book-1") -> dict[str, Any]:
        return dashboard_service.get_chapter(chapter_id, thread_id)

    @app.get("/api/logs")
    def get_logs(
            level: str | None = None,
            agent: str | None = None,
            chapter: int | None = None,
            limit: int = Query(default=200, ge=1, le=2000),
    ) -> list[dict[str, Any]]:
        return [_to_dict(entry) for entry in dashboard_service.get_logs(level=level, agent=agent, chapter=chapter, limit=limit)]

    @app.get("/api/output/files")
    def get_output_files() -> list[dict[str, Any]]:
        return dashboard_service.get_output_files()

    @app.get("/api/output/file")
    def get_output_file(path: str) -> dict[str, str]:
        try:
            return {"path": path, "content": dashboard_service.read_output_file(path)}
        except PathTraversalError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=path) from exc

    @app.get("/api/metrics")
    def get_metrics() -> dict[str, Any]:
        return dashboard_service.get_metrics()

    @app.get("/api/rag/status")
    def get_rag_status(thread_id: str = "book-1") -> dict[str, Any]:
        return dashboard_service.get_rag_status(thread_id)

    @app.post("/api/run")
    def run(command: RunCommand) -> dict[str, Any]:
        return dashboard_service.start_run(command.thread_id, fresh=command.fresh)

    @app.post("/api/resume")
    def resume(command: ThreadCommand) -> dict[str, Any]:
        return dashboard_service.resume(command.thread_id)

    @app.post("/api/regenerate-output")
    def regenerate_output(command: ThreadCommand) -> dict[str, Any]:
        return dashboard_service.regenerate_output(command.thread_id)

    @app.post("/api/chapters/{chapter_id}/patch")
    def patch_chapter(chapter_id: int, command: PatchChapterCommand) -> dict[str, Any]:
        return dashboard_service.patch_chapter(
            command.thread_id,
            chapter_id,
            command.markdown,
            regenerate_output=command.regenerate_output,
        )

    @app.post("/api/chapters/{chapter_id}/revise")
    def revise_chapter(chapter_id: int, command: ReviseChapterCommand) -> dict[str, Any]:
        return dashboard_service.revise_chapter(
            command.thread_id,
            chapter_id,
            command.feedback,
            regenerate_output=command.regenerate_output,
        )

    @app.post("/api/reset")
    def reset(command: ResetCommand) -> dict[str, Any]:
        try:
            return dashboard_service.reset_thread(command.thread_id, confirm=command.confirm)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.websocket("/api/events")
    async def events(websocket: WebSocket) -> None:
        await websocket.accept()
        while True:
            await websocket.send_json(
                {
                    "status": dashboard_service.get_status("book-1"),
                    "logs": [_to_dict(entry) for entry in dashboard_service.get_logs(limit=20)],
                }
            )
            await asyncio.sleep(1)

    dist = Path(web_dist) if web_dist is not None else Path("web/dist")
    if dist.exists():
        assets = dist / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}")
        def serve_spa(full_path: str = "") -> FileResponse:
            requested = (dist / full_path).resolve()
            dist_root = dist.resolve()
            if full_path and requested.is_file() and (requested == dist_root or dist_root in requested.parents):
                return FileResponse(requested)
            return FileResponse(dist / "index.html")

    return app


def _to_dict(value: object) -> dict[str, Any]:
    if isinstance(value, LogEntry):
        return {
            "timestamp": value.timestamp,
            "level": value.level,
            "logger": value.logger,
            "agent": value.agent,
            "message": value.message,
            "raw": value.raw,
            "chapter_id": value.chapter_id,
        }
    if isinstance(value, dict):
        return value
    return {}


app = create_app()
