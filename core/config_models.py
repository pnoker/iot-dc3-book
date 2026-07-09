"""
强类型应用配置模型
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class StrictConfigModel(BaseModel):
    """禁止未知配置项，避免 YAML 拼写错误静默失效。"""

    model_config = ConfigDict(extra="forbid")


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


class IllustrationConfig(StrictConfigModel):
    """全书图表规格标记与视觉约束。"""

    marker: str = "book-figure"
    renderer: str = "html-svg"
    theme: str = "technical-publication-light"
    palette: dict[str, str] = Field(default_factory=dict)
    allowed_types: list[str] = Field(default_factory=list)
    required_fields: list[str] = Field(default_factory=list)
    legend: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    example: str = ""


class StyleConfigModel(StrictConfigModel):
    tone: str = ""
    perspective: str = "第三人称"
    terminology: TerminologyConfig = Field(default_factory=TerminologyConfig)
    format: dict[str, str] = Field(default_factory=dict)
    illustrations: IllustrationConfig = Field(default_factory=IllustrationConfig)
    forbidden_words: list[str] = Field(default_factory=list)
    chapter_structure: list[str] = Field(default_factory=list)
    target_words_per_chapter: str = "4000-8000字"


class EmbeddingConfig(StrictConfigModel):
    base_url: str
    api_key: SecretStr
    model: str


class LLMConfig(StrictConfigModel):
    provider: str = "openai_compatible"
    base_url: str
    api_key: SecretStr
    model: str
    temperature: float = 0.7
    max_tokens: int = 8192
    embedding: EmbeddingConfig


class ReferenceSourceConfig(StrictConfigModel):
    """一个参考来源目录及其分类。

    - path 相对 project_dir 解析，label 用于溯源和命名空间。
    - categories 为该来源的基础分类标签（多标签）。
    - dir_categories 将子目录首段映射到追加的分类标签。
    - language 标注该来源语言，用于检索过滤。
    """

    path: str
    label: str
    categories: list[str]
    dir_categories: dict[str, list[str]] = Field(default_factory=dict)
    language: str = "zh"


class WebResearchConfig(StrictConfigModel):
    """可选在线证据补充配置。"""

    enabled: bool = False
    urls: list[str] = Field(default_factory=list)
    timeout_seconds: float = 10.0
    max_chars_per_url: int = 1800

    @model_validator(mode="after")
    def validate_web_research(self) -> WebResearchConfig:
        if self.timeout_seconds <= 0:
            raise ValueError("references.web_research.timeout_seconds 必须大于 0")
        if self.max_chars_per_url <= 0:
            raise ValueError("references.web_research.max_chars_per_url 必须大于 0")
        return self


class ReferenceConfig(StrictConfigModel):
    top_k: int = 5
    chunk_size: int = 1000
    chunk_overlap: int = 200
    sources: list[ReferenceSourceConfig]
    # 本书检索限定的分类（空=全局检索所有分类）
    query_categories: list[str] = Field(default_factory=list)
    # 混合检索开关（dense + BM25 + RRF）
    hybrid: bool = True
    # rerank 开关与候选数（默认关闭）
    rerank_enabled: bool = False
    rerank_candidates: int = 12
    # 知识精炼（Contextual Retrieval）开关（默认关闭）
    contextualize: bool = False
    # 在线资料补充（默认关闭；仅抓取显式 URL）
    web_research: WebResearchConfig = Field(default_factory=WebResearchConfig)

    @model_validator(mode="after")
    def validate_chunking(self) -> ReferenceConfig:
        if self.chunk_size <= 0:
            raise ValueError("references.chunk_size 必须大于 0")
        if self.chunk_overlap < 0:
            raise ValueError("references.chunk_overlap 不能小于 0")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("references.chunk_overlap 必须小于 chunk_size")
        if not self.sources:
            raise ValueError("references.sources 必须显式配置")
        return self


class OutputConfig(StrictConfigModel):
    dir: str = "./output"
    structure: str = "hierarchical"


class WritingConfig(StrictConfigModel):
    """出版级写作流水线配置。"""

    mode: Literal["draft", "publication"] = "publication"
    target_total_words: int = 200000
    default_chapter_target_words: int = 12000
    core_chapter_target_words: int = 16000
    light_chapter_target_words: int = 9000
    core_chapter_ids: list[int] = Field(default_factory=list)
    sectional_drafting: bool = True
    require_research_dossier: bool = True
    parallel_chapters: bool = True
    parallel_workers: int = 3

    @model_validator(mode="after")
    def validate_targets(self) -> WritingConfig:
        if self.target_total_words <= 0:
            raise ValueError("writing.target_total_words 必须大于 0")
        for field_name in ("default_chapter_target_words", "core_chapter_target_words", "light_chapter_target_words"):
            if getattr(self, field_name) <= 0:
                raise ValueError(f"writing.{field_name} 必须大于 0")
        if self.parallel_workers <= 0:
            raise ValueError("writing.parallel_workers 必须大于 0")
        return self


class QualityConfig(StrictConfigModel):
    """确定性出版质量门配置。"""

    enabled: bool = True
    mode: Literal["draft", "release"] = "release"
    min_words_per_chapter: int = 9000
    target_words_per_chapter: int = 12000
    max_words_over_target_ratio: float = 1.2
    min_heading_count: int = 8
    require_summary: bool = True
    require_exercises: bool = False
    min_exercise_count: int = 0
    min_figures_or_tables: int = 1
    min_figures_per_section: int = 1
    require_existing_local_images: bool = True
    forbid_placeholder_images: bool = True
    forbid_unsourced_statistics: bool = True
    forbid_unresolved_final_review: bool = True
    max_revision_rounds: int = 5
    max_final_revision_rounds: int = 1
    continue_on_failure: bool = True
    adversarial_review_enabled: bool = True
    originality_check_enabled: bool = True
    originality_max_overlap: float = 0.35
    originality_ngram: int = 5
    originality_min_paragraph_chars: int = 80

    @model_validator(mode="after")
    def validate_thresholds(self) -> QualityConfig:
        if self.min_words_per_chapter < 0:
            raise ValueError("quality.min_words_per_chapter 不能小于 0")
        if self.target_words_per_chapter < self.min_words_per_chapter:
            raise ValueError("quality.target_words_per_chapter 必须不小于 min_words_per_chapter")
        if self.max_words_over_target_ratio < 0:
            raise ValueError("quality.max_words_over_target_ratio 不能小于 0")
        if self.min_heading_count < 0:
            raise ValueError("quality.min_heading_count 不能小于 0")
        if self.min_exercise_count < 0:
            raise ValueError("quality.min_exercise_count 不能小于 0")
        if self.min_figures_or_tables < 0:
            raise ValueError("quality.min_figures_or_tables 不能小于 0")
        if self.min_figures_per_section < 0:
            raise ValueError("quality.min_figures_per_section 不能小于 0")
        if self.max_revision_rounds < 0:
            raise ValueError("quality.max_revision_rounds 不能小于 0")
        if self.max_final_revision_rounds < 0:
            raise ValueError("quality.max_final_revision_rounds 不能小于 0")
        if not 0.0 <= self.originality_max_overlap <= 1.0:
            raise ValueError("quality.originality_max_overlap 必须在 0.0 到 1.0 之间")
        if self.originality_ngram < 1:
            raise ValueError("quality.originality_ngram 不能小于 1")
        if self.originality_min_paragraph_chars < 0:
            raise ValueError("quality.originality_min_paragraph_chars 不能小于 0")
        return self


class AppConfig(StrictConfigModel):
    book: BookConfig
    parts: list[PartConfig]
    style: StyleConfigModel
    llm: LLMConfig
    references: ReferenceConfig
    output: OutputConfig = Field(default_factory=OutputConfig)
    writing: WritingConfig = Field(default_factory=WritingConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
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
