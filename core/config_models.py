"""
强类型应用配置模型
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StrictConfigModel(BaseModel):
    """禁止未知配置项，避免 YAML 拼写错误静默失效。"""

    model_config = ConfigDict(extra="forbid")


class EnvSettings(BaseSettings):
    """环境变量配置。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    deepseek_api_key: str = Field(default="", validation_alias="DEEPSEEK_API_KEY")
    openrouter_api_key: str = Field(default="", validation_alias="OPENROUTER_API_KEY")


class BookConfig(StrictConfigModel):
    title: str
    subtitle: str
    author: str = ""
    isbn: str = ""
    publisher: str = ""
    edition: str = "第一版"
    language: str = "zh-CN"


class ChapterConfig(StrictConfigModel):
    id: int
    title: str
    summary: str = ""


class PartConfig(StrictConfigModel):
    name: str
    prefix: str
    chapters: list[ChapterConfig]


class TerminologyConfig(StrictConfigModel):
    rule: str = ""
    example: str = ""


class StyleConfigModel(StrictConfigModel):
    tone: str = ""
    perspective: str = "第三人称"
    terminology: TerminologyConfig = Field(default_factory=TerminologyConfig)
    format: dict[str, str] = Field(default_factory=dict)
    forbidden_words: list[str] = Field(default_factory=list)
    chapter_structure: list[str] = Field(default_factory=list)
    target_words_per_chapter: str = "4000-8000字"


class EmbeddingConfig(StrictConfigModel):
    base_url: str = ""
    api_key: str = ""
    model: str = "openai/text-embedding-3-small"


class LLMConfig(StrictConfigModel):
    provider: str = "openai_compatible"
    base_url: str = "https://api.deepseek.com"
    api_key: str = ""
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 8192
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)


class ReferenceConfig(StrictConfigModel):
    books_dir: str = "../books"
    top_k: int = 5
    chunk_size: int = 1000
    chunk_overlap: int = 200

    @model_validator(mode="after")
    def validate_chunking(self) -> ReferenceConfig:
        if self.chunk_size <= 0:
            raise ValueError("references.chunk_size 必须大于 0")
        if self.chunk_overlap < 0:
            raise ValueError("references.chunk_overlap 不能小于 0")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("references.chunk_overlap 必须小于 chunk_size")
        return self


class OutputConfig(StrictConfigModel):
    dir: str = "./output"
    structure: str = "hierarchical"


class AppConfig(StrictConfigModel):
    book: BookConfig
    parts: list[PartConfig]
    style: StyleConfigModel
    llm: LLMConfig
    references: ReferenceConfig = Field(default_factory=ReferenceConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    author: dict[str, Any] = Field(default_factory=dict)
    config_dir: Path = Field(default_factory=lambda: Path("config").resolve(), exclude=True)
    project_dir: Path = Field(default_factory=Path.cwd, exclude=True)

    @model_validator(mode="after")
    def validate_parts(self) -> AppConfig:
        if not self.parts:
            raise ValueError("parts 必须是非空列表")
        if not any(part.chapters for part in self.parts):
            raise ValueError("parts 中至少需要一个章节")
        return self

    def with_env_settings(self, env_settings: EnvSettings) -> AppConfig:
        """使用环境变量覆盖敏感配置。"""
        return self.model_copy(
            update={
                "llm": self.llm.model_copy(
                    update={
                        "api_key": env_settings.deepseek_api_key or self.llm.api_key,
                        "embedding": self.llm.embedding.model_copy(
                            update={
                                "api_key": env_settings.openrouter_api_key or self.llm.embedding.api_key,
                            }
                        ),
                    }
                )
            }
        )
