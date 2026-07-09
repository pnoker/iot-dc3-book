"""
公共工具函数
"""

from __future__ import annotations

import json
from typing import Any

from core.log import get_logger

logger = get_logger("utils")


def parse_json_from_llm(response: str) -> dict[str, Any]:
    """
    从 LLM 响应中解析严格 JSON object。

    Args:
        response: LLM 原始响应文本

    Returns:
        解析后的 dict

    Raises:
        ValueError: 所有解析方式均失败
    """
    try:
        parsed = json.loads(response.strip())
    except json.JSONDecodeError as exc:
        logger.error("JSON 解析失败，响应前 200 字: %s", response[:200])
        raise ValueError(f"无法从 LLM 响应中解析 JSON: {response[:100]}...") from exc
    if not isinstance(parsed, dict):
        raise ValueError("LLM JSON 响应必须是 object")
    return {str(k): v for k, v in parsed.items()}


def truncate(text: str, max_len: int = 500, suffix: str = "...") -> str:
    """截断文本"""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix
