"""
极简配置模型与加载 —— 纯写作分支，仅保留组装和导出的必要配置。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class BookConfig(BaseModel):
    """书籍基本信息。"""
    title: str
    subtitle: str
    author: str = ""
    isbn: str = ""
    publisher: str = ""
    edition: str = "第一版"
    language: str = "zh-CN"


class ChapterConfig(BaseModel):
    """篇章中的章节 — 只保留 id 和 title，其余 agent 字段已移除。"""
    id: int
    title: str


class PartConfig(BaseModel):
    """篇章结构。"""
    name: str
    prefix: str
    chapters: list[ChapterConfig]


class IllustrationConfig(BaseModel):
    """全书图表规格标记与视觉约束。"""
    marker: str = "book-figure"
    renderer: str = "html-svg"
    theme: str = "technical-publication-light"
    palette: dict[str, str] = Field(default_factory=dict)
    allowed_types: list[str] = Field(default_factory=list)
    required_fields: list[str] = Field(default_factory=list)


class StyleConfig(BaseModel):
    """写作风格配置 — 仅保留图表渲染相关，去掉 agent 写作指导字段。"""
    illustrations: IllustrationConfig = Field(default_factory=IllustrationConfig)


class OutputConfig(BaseModel):
    """输出配置。"""
    dir: str = "./output"
    structure: str = "hierarchical"
    pandoc_bin: str = "pandoc"


class AppConfig(BaseModel):
    """应用配置 — 只保留组装导出必要的顶层配置。"""
    model_config = ConfigDict(extra="ignore")

    book: BookConfig
    parts: list[PartConfig]
    style: StyleConfig = Field(default_factory=StyleConfig)
    author: dict[str, Any] = Field(default_factory=dict)
    output: OutputConfig = Field(default_factory=OutputConfig)


def load_config(config_dir: str = "book/config") -> AppConfig:
    """从配置目录加载并合并所有 .yaml 文件为 AppConfig。"""
    config_path = Path(config_dir)
    if not config_path.is_dir():
        raise FileNotFoundError(f"配置目录不存在: {config_dir}")

    yaml_files = sorted(config_path.glob("*.yaml"))
    if not yaml_files:
        raise FileNotFoundError(f"配置目录中没有 .yaml 文件: {config_dir}")

    merged: dict[str, Any] = {}
    for yf in yaml_files:
        with open(yf, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            continue
        merged[yf.stem] = data

    app_config = AppConfig.model_validate(merged)

    total_chapters = sum(len(p.chapters) for p in app_config.parts)
    from book_builder.log import get_logger
    logger = get_logger("config")
    logger.info("配置已加载: %d 篇, %d 章", len(app_config.parts), total_chapters)
    return app_config
