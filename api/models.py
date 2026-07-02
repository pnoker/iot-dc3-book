"""Dashboard API DTO。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class ThreadCommand(BaseModel):
    thread_id: str = "book-1"


class RunCommand(ThreadCommand):
    fresh: bool = False


class PatchChapterCommand(ThreadCommand):
    markdown: str
    regenerate_output: bool = False


class ReviseChapterCommand(ThreadCommand):
    feedback: str
    regenerate_output: bool = False


class ResetCommand(ThreadCommand):
    confirm: str
