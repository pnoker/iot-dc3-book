"""
配置加载与校验 - 从 config/ 目录加载多文件配置
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml
from dotenv import dotenv_values
from pydantic import SecretStr

from core.config_models import AppConfig
from core.log import get_logger
from core.rag_sources import ReferenceSource
from core.state import BookState, ChapterPlan, PartPlan, QualitySettings, StyleConfig, WritingSettings

logger = get_logger("config")

ConfigDict = dict[str, Any]
EnvDict = dict[str, str]

_ENV_PLACEHOLDER_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass(frozen=True)
class ConfigPaths:
    """配置派生路径，全部解析为绝对路径。"""

    config_dir: Path
    project_dir: Path
    reference_sources: tuple[ReferenceSource, ...]
    output_dir: Path
    data_dir: Path
    chroma_dir: Path
    rag_manifest: Path
    bm25_index: Path


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
    return _load_config_dir(path.resolve())


def load_app_config(config_path: str = "config") -> AppConfig:
    """一次性加载、校验并返回强类型应用配置。"""
    config_dir = Path(config_path).resolve()
    cfg = load_config(str(config_dir))
    return config_to_app_config(cfg, config_dir=config_dir)


def load_env_settings(env_path: Path = Path(".env")) -> EnvDict:
    """加载通用环境变量映射；shell 环境变量优先于 .env。"""
    values: EnvDict = {key: value for key, value in dotenv_values(env_path).items() if value is not None}
    values.update(os.environ)
    return values


def resolve_env_reference(value: str, env: EnvDict, *, location: str) -> str:
    """解析单个字符串中的 ${VAR}，缺失变量立即报错。"""
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        env_value = env.get(name)
        if env_value is None or env_value == "":
            missing.append(name)
            return ""
        return env_value

    resolved = _ENV_PLACEHOLDER_RE.sub(replace, value)
    if missing:
        names = "、".join(sorted(set(missing)))
        raise ValueError(f"配置 {location} 引用了未设置的环境变量: {names}")
    return resolved


def reveal_secret(value: SecretStr | str) -> str:
    """显式取出 SecretStr，仅用于构造外部客户端参数。"""
    return value.get_secret_value() if isinstance(value, SecretStr) else value


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
    _validate_config(merged, config_dir)
    return merged


def _validate_config(cfg: ConfigDict, config_dir: Path | None = None) -> None:
    """基础配置校验"""
    app_config = config_to_app_config(cfg, config_dir=config_dir)
    total_chapters = sum(len(p.chapters) for p in app_config.parts)
    logger.debug("配置校验通过: %d 篇, %d 章", len(app_config.parts), total_chapters)


def config_to_app_config(cfg: ConfigDict, config_dir: Path | None = None) -> AppConfig:
    """将配置字典转换为强类型 AppConfig。"""
    resolved_config_dir = (config_dir or Path("config")).resolve()
    project_dir = resolved_config_dir.parent
    env_path = project_dir / ".env"
    resolved_cfg = _resolve_env_placeholders(cfg, load_env_settings(env_path))
    app_config = AppConfig.model_validate(
        {
            **resolved_cfg,
            "config_dir": resolved_config_dir,
            "project_dir": project_dir,
        }
    )
    return app_config


def config_to_book_state(cfg: ConfigDict | AppConfig) -> BookState:
    """将配置转换为 BookState"""
    app_config = cfg if isinstance(cfg, AppConfig) else config_to_app_config(cfg)

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
        writing=WritingSettings(**app_config.writing.model_dump()),
        quality=QualitySettings(**app_config.quality.model_dump()),
    )
    logger.info("BookState 初始化: %s, %d 章", state.book_title, sum(len(p.chapters) for p in parts))
    return state


def get_config_paths(app_config: AppConfig) -> ConfigPaths:
    """根据强类型配置计算所有运行时路径。"""
    project_dir = app_config.project_dir.resolve()
    config_dir = app_config.config_dir.resolve()
    reference_sources = _resolve_reference_sources(app_config, project_dir)
    output_dir = _resolve_path(app_config.output.dir, project_dir)
    data_dir = project_dir / ".data"
    return ConfigPaths(
        config_dir=config_dir,
        project_dir=project_dir,
        reference_sources=reference_sources,
        output_dir=output_dir,
        data_dir=data_dir,
        chroma_dir=data_dir / "chroma",
        rag_manifest=data_dir / "rag_index.json",
        bm25_index=data_dir / "bm25_index.json",
    )


def get_llm_config(cfg: ConfigDict | AppConfig) -> ConfigDict:
    """获取 Chat LLM 配置"""
    llm = (cfg if isinstance(cfg, AppConfig) else config_to_app_config(cfg)).llm
    return {
        "base_url": llm.base_url,
        "api_key": reveal_secret(llm.api_key),
        "model": llm.model,
        "temperature": llm.temperature,
        "max_tokens": llm.max_tokens,
    }


def get_embed_config(cfg: ConfigDict | AppConfig) -> ConfigDict:
    """获取 Embedding 配置"""
    emb = (cfg if isinstance(cfg, AppConfig) else config_to_app_config(cfg)).llm.embedding
    return {
        "embed_base_url": emb.base_url,
        "embed_api_key": reveal_secret(emb.api_key),
        "embed_model": emb.model,
    }


def _resolve_reference_sources(app_config: AppConfig, project_dir: Path) -> tuple[ReferenceSource, ...]:
    """解析显式参考来源。"""
    resolved: list[ReferenceSource] = []
    for source in app_config.references.sources:
        path = _resolve_path(source.path, project_dir)
        dir_categories = tuple((name, tuple(tags)) for name, tags in source.dir_categories.items())
        resolved.append(
            ReferenceSource(
                path=path,
                label=source.label,
                categories=tuple(source.categories),
                dir_categories=dir_categories,
                language=source.language,
            )
        )
    return tuple(resolved)


def _resolve_path(value: str, base_dir: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (base_dir / path).resolve()


def _resolve_env_placeholders(value: Any, env: EnvDict, location: str = "配置") -> Any:
    if isinstance(value, dict):
        return {key: _resolve_env_placeholders(item, env, f"{location}.{key}") for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_env_placeholders(item, env, f"{location}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, str):
        return resolve_env_reference(value, env, location=location)
    return value
