"""
配置加载与校验 - 从 config/ 目录加载多文件配置
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from core.config_models import AppConfig, EnvSettings
from core.log import get_logger
from core.state import BookState, ChapterPlan, PartPlan, StyleConfig

logger = get_logger("config")


ConfigDict = dict[str, Any]


def load_config(config_path: str = "config") -> ConfigDict:
    """
    加载配置目录，自动合并目录下所有 .yaml 文件。

    Args:
        config_path: 配置目录路径

    Returns:
        合并后的配置字典
    """
    path = Path(config_path)

    if not path.is_dir():
        raise FileNotFoundError(f"配置目录不存在: {config_path}")
    return _load_config_dir(path)


def load_env_settings(env_path: Path = Path(".env")) -> EnvSettings:
    """使用 pydantic-settings 加载环境变量和 .env。"""
    settings_cls = cast("Any", EnvSettings)
    return cast("EnvSettings", settings_cls(_env_file=env_path))


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


def _validate_config(cfg: ConfigDict) -> None:
    """基础配置校验"""
    app_config = config_to_app_config(cfg)
    total_chapters = sum(len(p.chapters) for p in app_config.parts)
    logger.debug("配置校验通过: %d 篇, %d 章", len(app_config.parts), total_chapters)


def config_to_app_config(cfg: ConfigDict) -> AppConfig:
    """将配置字典转换为强类型 AppConfig。"""
    return AppConfig.model_validate(cfg).with_env_settings(load_env_settings())


def config_to_book_state(cfg: ConfigDict) -> BookState:
    """将配置转换为 BookState"""
    app_config = config_to_app_config(cfg)

    parts: list[PartPlan] = []
    for part_cfg in app_config.parts:
        chapters = [ChapterPlan(id=ch.id, title=ch.title, summary=ch.summary) for ch in part_cfg.chapters]
        parts.append(PartPlan(name=part_cfg.name, prefix=part_cfg.prefix, chapters=chapters))

    style_cfg = app_config.style
    style = StyleConfig(
        tone=style_cfg.tone,
        perspective=style_cfg.perspective,
        terminology_rule=style_cfg.terminology.rule,
        forbidden_words=style_cfg.forbidden_words,
        chapter_structure=style_cfg.chapter_structure,
        target_words_per_chapter=style_cfg.target_words_per_chapter,
        format_rules=style_cfg.format,
    )

    state = BookState(
        book_title=app_config.book.title,
        book_subtitle=app_config.book.subtitle,
        author=app_config.book.author,
        parts=parts,
        style=style,
    )
    logger.info("BookState 初始化: %s, %d 章", state.book_title, sum(len(p.chapters) for p in parts))
    return state


def get_references_dir(cfg: ConfigDict, config_path: str = "config") -> Path:
    """获取参考书籍目录的绝对路径"""
    app_config = config_to_app_config(cfg)
    ref_dir = app_config.references.books_dir
    config_dir = Path(config_path).resolve()
    return (config_dir / ref_dir).resolve()


def get_llm_config(cfg: ConfigDict) -> ConfigDict:
    """获取 Chat LLM 配置"""
    llm = config_to_app_config(cfg).llm
    return {
        "base_url": llm.base_url,
        "api_key": llm.api_key,
        "model": llm.model,
        "temperature": llm.temperature,
        "max_tokens": llm.max_tokens,
    }


def get_embed_config(cfg: ConfigDict) -> ConfigDict:
    """获取 Embedding 配置"""
    emb = config_to_app_config(cfg).llm.embedding
    return {
        "embed_base_url": emb.base_url,
        "embed_api_key": emb.api_key,
        "embed_model": emb.model,
    }
