"""
配置加载与校验 - 从 config/ 目录加载多文件配置
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

import yaml

from core.log import get_logger
from core.state import BookState, ChapterPlan, PartPlan, StyleConfig

logger = get_logger("config")


ConfigDict = dict[str, Any]


def load_config(config_path: str = "config") -> ConfigDict:
    """
    加载配置。支持两种模式：
    1. 目录模式：传入 config/ 目录路径，自动合并目录下所有 .yaml 文件
    2. 文件模式：传入单个 .yaml 文件路径（向后兼容）

    Args:
        config_path: 配置目录或文件路径

    Returns:
        合并后的配置字典
    """
    path = Path(config_path)

    if path.is_dir():
        return _load_config_dir(path)
    elif path.is_file():
        return _load_config_file(path)
    else:
        raise FileNotFoundError(f"配置路径不存在: {config_path}")


def _load_config_dir(config_dir: Path) -> ConfigDict:
    """从目录加载并合并所有 YAML 配置文件"""
    yaml_files = sorted(config_dir.glob("*.yaml"))
    if not yaml_files:
        raise FileNotFoundError(f"配置目录中没有 .yaml 文件: {config_dir}")

    merged: ConfigDict = {}
    for yf in yaml_files:
        with open(yf, encoding="utf-8") as f:
            data = cast("ConfigDict | None", yaml.safe_load(f))
        if data is None:
            continue

        key = yf.stem  # 文件名（不含扩展名）作为 key
        merged[key] = data
        logger.debug("加载配置: %s", yf.name)

    logger.info("配置已加载: %s (%d 个文件)", config_dir, len(yaml_files))
    _validate_config(merged)
    return merged


def _load_config_file(config_path: Path) -> ConfigDict:
    """加载单个 YAML 配置文件（向后兼容）"""
    with open(config_path, encoding="utf-8") as f:
        cfg = cast("ConfigDict", yaml.safe_load(f))
    logger.info("配置已加载: %s", config_path)
    _validate_config(cfg)
    return cfg


def _validate_config(cfg: ConfigDict) -> None:
    """基础配置校验"""
    # 目录模式：检查必需的顶层 key
    required_keys = ["book", "parts", "style", "llm"]
    for key in required_keys:
        if key not in cfg:
            raise ValueError(f"配置缺少必填字段: {key} (检查 config/{key}.yaml)")

    book = cfg["book"]
    for key in ("title", "subtitle"):
        if not book.get(key):
            raise ValueError(f"book.{key} 不能为空")

    parts = cfg["parts"]
    if not isinstance(parts, list) or len(parts) == 0:
        raise ValueError("parts 必须是非空列表")

    total_chapters = sum(len(p.get("chapters", [])) for p in parts)
    if total_chapters == 0:
        raise ValueError("parts 中至少需要一个章节")

    logger.debug("配置校验通过: %d 篇, %d 章", len(parts), total_chapters)


def config_to_book_state(cfg: ConfigDict) -> BookState:
    """将配置转换为 BookState"""
    book_cfg = cfg.get("book", {})
    parts_cfg = cfg.get("parts", [])
    style_cfg = cfg.get("style", {})

    parts: list[PartPlan] = []
    for p in parts_cfg:
        chapters = [
            ChapterPlan(id=ch["id"], title=ch["title"], summary=ch.get("summary", "")) for ch in p.get("chapters", [])
        ]
        parts.append(PartPlan(name=p["name"], prefix=p["prefix"], chapters=chapters))

    terminology = style_cfg.get("terminology", {})
    style = StyleConfig(
        tone=style_cfg.get("tone", ""),
        perspective=style_cfg.get("perspective", "第三人称"),
        terminology_rule=terminology.get("rule", "") if isinstance(terminology, dict) else "",
        forbidden_words=style_cfg.get("forbidden_words", []),
        chapter_structure=style_cfg.get("chapter_structure", []),
        target_words_per_chapter=style_cfg.get("target_words_per_chapter", "4000-8000字"),
        format_rules=style_cfg.get("format", {}),
    )

    state = BookState(
        book_title=book_cfg.get("title", ""),
        book_subtitle=book_cfg.get("subtitle", ""),
        author=book_cfg.get("author", ""),
        parts=parts,
        style=style,
    )
    logger.info("BookState 初始化: %s, %d 章", state.book_title, sum(len(p.chapters) for p in parts))
    return state


def get_references_dir(cfg: ConfigDict, config_path: str = "config") -> Path:
    """获取参考书籍目录的绝对路径"""
    references = cast("ConfigDict", cfg.get("references", {}))
    ref_dir = str(references.get("books_dir", "../books"))
    base = Path(config_path).resolve()
    config_dir = base.parent if base.is_file() else base
    return (config_dir / ref_dir).resolve()


def get_llm_config(cfg: ConfigDict) -> ConfigDict:
    """获取 Chat LLM 配置"""
    llm = cfg.get("llm", {})
    api_key = _resolve_env_var(llm.get("api_key", ""))
    return {
        "base_url": llm.get("base_url", "https://api.deepseek.com"),
        "api_key": api_key,
        "model": llm.get("model", "deepseek-chat"),
        "temperature": llm.get("temperature", 0.7),
        "max_tokens": llm.get("max_tokens", 8192),
    }


def get_embed_config(cfg: ConfigDict) -> ConfigDict:
    """获取 Embedding 配置"""
    emb = cfg.get("llm", {}).get("embedding", {})
    api_key = _resolve_env_var(emb.get("api_key", ""))
    return {
        "embed_base_url": emb.get("base_url", ""),
        "embed_api_key": api_key,
        "embed_model": emb.get("model", "openai/text-embedding-3-small"),
    }


def _resolve_env_var(value: str) -> str:
    """解析 ${VAR_NAME} 格式的环境变量"""
    if value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]
        resolved = os.environ.get(env_var, "")
        if not resolved:
            logger.warning("环境变量 %s 未设置", env_var)
        return resolved
    return value
