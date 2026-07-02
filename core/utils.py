"""
公共工具函数
"""

from __future__ import annotations

import json
from typing import Any

from json_repair import repair_json

from core.log import get_logger

logger = get_logger("utils")


def parse_json_from_llm(response: str) -> dict[str, Any]:
    """
    从 LLM 响应中提取并解析 JSON。

    LLM 经常在 JSON 前后包裹 ```json ... ``` 或纯文本，
    此函数尝试多种方式提取。

    Args:
        response: LLM 原始响应文本

    Returns:
        解析后的 dict

    Raises:
        ValueError: 所有解析方式均失败
    """
    candidates: list[str] = []

    # 方式 1: 提取 ```json ... ``` 块
    if "```json" in response:
        try:
            json_str = response.split("```json")[1].split("```")[0].strip()
            candidates.append(json_str)
        except (IndexError, ValueError):
            pass

    # 方式 2: 提取 ``` ... ``` 块（无 json 标记）
    if "```" in response and "```json" not in response:
        try:
            parts = response.split("```")
            if len(parts) >= 3:
                candidates.append(parts[1].strip())
        except (IndexError, ValueError):
            pass

    # 方式 3: 直接尝试解析整个响应
    candidates.append(response.strip())

    # 方式 4: 查找第一个 { 到最后一个 }
    first_brace = response.find("{")
    last_brace = response.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidates.append(response[first_brace : last_brace + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return {str(k): v for k, v in parsed.items()}
        except json.JSONDecodeError:
            try:
                repaired = json.loads(repair_json(candidate))
                if isinstance(repaired, dict):
                    return {str(k): v for k, v in repaired.items()}
            except (json.JSONDecodeError, ValueError):
                continue

    logger.error("JSON 解析失败，响应前 200 字: %s", response[:200])
    raise ValueError(f"无法从 LLM 响应中解析 JSON: {response[:100]}...")


def truncate(text: str, max_len: int = 500, suffix: str = "...") -> str:
    """截断文本"""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix
