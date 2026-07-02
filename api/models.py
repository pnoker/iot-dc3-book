"""Dashboard API DTO。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
