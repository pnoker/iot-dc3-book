"""
核心状态定义 - 所有 Agent 共享的数据结构
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ChapterStatus = Literal[
    "pending",
    "researched",
    "written",
    "fact_checked",
    "styled",
    "reviewed",
    "approved",
    "quality_failed",
]
SectionStatus = Literal["pending", "written", "assembled", "reviewed", "review_failed"]


class StyleConfig(BaseModel):
    """写作风格配置"""

    tone: str = ""
    perspective: str = "第三人称"
    terminology_rule: str = ""
    forbidden_words: list[str] = Field(default_factory=list)
    chapter_structure: list[str] = Field(default_factory=list)
    target_words_per_chapter: str = "4000-8000字"
    format_rules: dict[str, str] = Field(default_factory=dict)
    illustrations: dict[str, Any] = Field(default_factory=dict)


class WritingSettings(BaseModel):
    """出版级写作流水线运行参数。"""

    mode: Literal["draft", "publication"] = "publication"
    target_total_words: int = 200000
    default_chapter_target_words: int = 12000
    core_chapter_target_words: int = 16000
    light_chapter_target_words: int = 9000
    core_chapter_ids: list[int] = Field(default_factory=list)
    sectional_drafting: bool = True
    require_research_dossier: bool = True

    def target_for_chapter(self, chapter_id: int) -> int:
        """返回章节目标字数。"""
        return self.core_chapter_target_words if chapter_id in self.core_chapter_ids else self.default_chapter_target_words


class QualitySettings(BaseModel):
    """确定性出版质量门运行参数。"""

    enabled: bool = False
    mode: Literal["draft", "release"] = "draft"
    min_words_per_chapter: int = 0
    target_words_per_chapter: int = 0
    max_words_over_target_ratio: float = 1.2
    min_heading_count: int = 0
    require_summary: bool = False
    require_exercises: bool = False
    min_exercise_count: int = 0
    min_figures_or_tables: int = 0
    min_figures_per_section: int = 1
    require_existing_local_images: bool = False
    forbid_placeholder_images: bool = False
    forbid_unsourced_statistics: bool = False
    forbid_unresolved_final_review: bool = False
    max_revision_rounds: int = 10
    max_final_revision_rounds: int = 1
    continue_on_failure: bool = True


class BlueprintSection(BaseModel):
    """章节蓝图中的一个小节。"""

    section_id: str = ""
    title: str = ""
    parent_title: str = ""
    heading: str
    target_words: int = 1200
    purpose: str = ""
    key_points: list[str] = Field(default_factory=list)
    evidence_needed: list[str] = Field(default_factory=list)
    required_elements: list[str] = Field(default_factory=list)


class ChapterBlueprint(BaseModel):
    """出版级章节蓝图。"""

    chapter_id: int
    title: str
    target_words: int = 12000
    reader_outcome: str = ""
    thesis: str = ""
    sections: list[BlueprintSection] = Field(default_factory=list)
    case_studies: list[str] = Field(default_factory=list)
    figures: list[str] = Field(default_factory=list)
    tables: list[str] = Field(default_factory=list)
    code_examples: list[str] = Field(default_factory=list)
    learning_goals: list[str] = Field(default_factory=list)


class EvidenceNote(BaseModel):
    """可用于写作和核查的证据摘录。"""

    id: str
    source_type: Literal["local", "web"] = "local"
    source: str
    locator: str = ""
    excerpt: str


class ResearchDossier(BaseModel):
    """章节研究资料包。"""

    chapter_id: int
    queries: list[str] = Field(default_factory=list)
    key_claims: list[str] = Field(default_factory=list)
    evidence_notes: list[EvidenceNote] = Field(default_factory=list)
    source_notes: list[str] = Field(default_factory=list)
    web_notes: list[str] = Field(default_factory=list)
    evidence_policy: str = ""
    risks: list[str] = Field(default_factory=list)


class SectionPlan(BaseModel):
    """三级写作单元规划，例如 1.1.1。"""

    id: str
    chapter_id: int
    title: str
    heading: str
    parent_title: str = ""
    target_words: int = 1200
    purpose: str = ""
    key_points: list[str] = Field(default_factory=list)
    evidence_needed: list[str] = Field(default_factory=list)
    required_elements: list[str] = Field(default_factory=list)
    status: SectionStatus = "pending"


class ChapterPlan(BaseModel):
    """单章规划"""

    id: int
    title: str
    summary: str = ""
    outline: str = ""  # 详细大纲（Planner 生成）
    key_points: list[str] = Field(default_factory=list)
    blueprint: ChapterBlueprint | None = None
    sections: list[SectionPlan] = Field(default_factory=list)
    research_dossier: ResearchDossier | None = None
    foreshadows_planted: list[str] = Field(default_factory=list)
    foreshadows_resolved: list[str] = Field(default_factory=list)
    status: ChapterStatus = "pending"


class PartPlan(BaseModel):
    """篇章规划"""

    name: str  # 基础篇 / 技术篇 / 应用篇
    prefix: str  # 一 / 二 / 三
    chapters: list[ChapterPlan] = Field(default_factory=list)


class ForeshadowItem(BaseModel):
    """伏笔条目"""

    id: str
    description: str
    planted_chapter: int
    planned_resolve_chapter: int
    status: Literal["planted", "resolved", "abandoned"] = "planted"
    context: str = ""


class ChapterContent(BaseModel):
    """已写章节内容"""

    chapter_id: int
    title: str
    markdown: str
    word_count: int = 0
    review_feedback: str = ""
    style_feedback: str = ""
    fact_feedback: str = ""
    citation_feedback: str = ""
    publication_feedback: str = ""
    revision_feedback: str = ""
    revision_count: int = 0
    # Editor 对本章伏笔任务的核验结论 [{id, type, done}]，供质量门通过时转移伏笔状态
    foreshadow_checks: list[dict[str, Any]] = Field(default_factory=list)


class SectionContent(BaseModel):
    """已写三级小节内容。"""

    section_id: str
    chapter_id: int
    title: str
    markdown: str
    word_count: int = 0
    review_feedback: str = ""
    style_feedback: str = ""
    fact_feedback: str = ""
    citation_feedback: str = ""
    revision_feedback: str = ""
    revision_count: int = 0


class ReferenceChunk(BaseModel):
    """参考书籍检索结果"""

    source_file: str
    chapter_or_section: str
    text: str
    relevance_score: float = 0.0


class BookState(BaseModel):
    """
    出版级写作全局状态 - 所有 Agent 读写此状态。

    设计原则：
    - 所有字段使用 Pydantic BaseModel 以支持序列化
    - 使用 Literal 约束有限状态
    - 提供便捷方法封装常见操作
    """

    # --- 配置 ---
    book_title: str = ""
    book_subtitle: str = ""
    author: str = ""

    # --- 全局规划 ---
    parts: list[PartPlan] = Field(default_factory=list)
    foreshadows: list[ForeshadowItem] = Field(default_factory=list)
    style: StyleConfig = Field(default_factory=StyleConfig)
    writing: WritingSettings = Field(default_factory=WritingSettings)
    quality: QualitySettings = Field(default_factory=QualitySettings)

    # --- 当前执行位置 ---
    current_phase: Literal[
        "init",
        "indexing",
        "planning",
        "plan_review",
        "writing",
        "final_review",
        "completed",
    ] = "init"
    current_part_idx: int = 0
    current_chapter_idx: int = 0
    current_section_id: str = ""

    # --- 已完成内容 ---
    section_contents: list[SectionContent] = Field(default_factory=list)
    chapters: list[ChapterContent] = Field(default_factory=list)

    # --- 参考资料 ---
    reference_chunks: list[ReferenceChunk] = Field(default_factory=list)

    # --- 流转控制 ---
    needs_revision: bool = False
    revision_target_chapter: int = 0
    max_revision_count: int = 3
    error_message: str = ""
    # 大纲评审：是否需重规划、已重规划次数与上限（防评审-重规划死循环）
    plan_needs_revision: bool = False
    plan_revision_count: int = 0
    max_plan_revision_count: int = 2
    # 终审：需返修的章节 id 列表、已终审返修轮次与上限
    final_revision_chapters: list[int] = Field(default_factory=list)
    final_revision_round: int = 0
    max_final_revision_round: int = 1
    publication_approved: bool = False

    # --- 最终输出 ---
    output_dir: str = ""
    toc_markdown: str = ""
    final_report: str = ""

    # ---- 便捷方法 ----

    def get_current_chapter(self) -> ChapterPlan | None:
        """获取当前正在处理的章节规划"""
        if 0 <= self.current_part_idx < len(self.parts):
            part = self.parts[self.current_part_idx]
            if 0 <= self.current_chapter_idx < len(part.chapters):
                return part.chapters[self.current_chapter_idx]
        return None

    def get_current_part(self) -> PartPlan | None:
        """获取当前篇章"""
        if 0 <= self.current_part_idx < len(self.parts):
            return self.parts[self.current_part_idx]
        return None

    def get_all_chapters_flat(self) -> list[ChapterPlan]:
        """获取所有章节的扁平列表"""
        result: list[ChapterPlan] = []
        for part in self.parts:
            result.extend(part.chapters)
        return result

    def get_all_sections_flat(self) -> list[SectionPlan]:
        """获取所有三级写作单元的扁平列表。"""
        result: list[SectionPlan] = []
        for chapter in self.get_all_chapters_flat():
            result.extend(chapter.sections)
        return result

    def get_current_section(self) -> SectionPlan | None:
        """获取当前三级写作单元。"""
        if self.current_section_id:
            return self.get_section_plan(self.current_section_id)
        chapter = self.get_current_chapter()
        return chapter.sections[0] if chapter and chapter.sections else None

    def get_section_plan(self, section_id: str) -> SectionPlan | None:
        """按稳定编号获取三级写作单元规划。"""
        for section in self.get_all_sections_flat():
            if section.id == section_id:
                return section
        return None

    def set_current_section_by_id(self, section_id: str) -> bool:
        """将当前执行位置切换到指定三级写作单元。"""
        for part_idx, part in enumerate(self.parts):
            for chapter_idx, chapter in enumerate(part.chapters):
                for section in chapter.sections:
                    if section.id == section_id:
                        self.current_part_idx = part_idx
                        self.current_chapter_idx = chapter_idx
                        self.current_section_id = section_id
                        return True
        return False

    def get_chapter_content(self, chapter_id: int) -> ChapterContent | None:
        """按 ID 获取已写章节内容"""
        for ch in self.chapters:
            if ch.chapter_id == chapter_id:
                return ch
        return None

    def get_section_content(self, section_id: str) -> SectionContent | None:
        """按稳定编号获取已写三级小节。"""
        for section in self.section_contents:
            if section.section_id == section_id:
                return section
        return None

    def upsert_section_content(self, content: SectionContent) -> None:
        """按三级小节编号新增或替换正文。"""
        for idx, existing in enumerate(self.section_contents):
            if existing.section_id == content.section_id:
                self.section_contents[idx] = content
                return
        self.section_contents.append(content)

    def get_chapter_section_contents(self, chapter_id: int) -> list[SectionContent]:
        """按章节规划顺序返回该章已写小节。"""
        chapter = next((item for item in self.get_all_chapters_flat() if item.id == chapter_id), None)
        if chapter is None:
            return []
        by_id = {item.section_id: item for item in self.section_contents if item.chapter_id == chapter_id}
        return [by_id[section.id] for section in chapter.sections if section.id in by_id]

    def upsert_chapter_content(self, content: ChapterContent) -> None:
        """按章节 ID 新增或替换正文，确保状态中同一章节只有一份正文。"""
        for idx, existing in enumerate(self.chapters):
            if existing.chapter_id == content.chapter_id:
                self.chapters[idx] = content
                return
        self.chapters.append(content)

    def remove_chapter_content(self, chapter_id: int) -> None:
        """移除指定章节正文。"""
        self.chapters = [ch for ch in self.chapters if ch.chapter_id != chapter_id]

    def set_current_chapter_by_id(self, chapter_id: int) -> bool:
        """将当前执行位置切换到指定章节。"""
        for part_idx, part in enumerate(self.parts):
            for chapter_idx, chapter in enumerate(part.chapters):
                if chapter.id == chapter_id:
                    self.current_part_idx = part_idx
                    self.current_chapter_idx = chapter_idx
                    self.current_section_id = chapter.sections[0].id if chapter.sections else ""
                    return True
        return False

    def clear_chapter_feedback(self, chapter_id: int) -> None:
        """清空指定章节的质量反馈和修订标记。"""
        content = self.get_chapter_content(chapter_id)
        if content:
            content.review_feedback = ""
            content.style_feedback = ""
            content.fact_feedback = ""
            content.citation_feedback = ""
            content.publication_feedback = ""
        if self.revision_target_chapter in (0, chapter_id):
            self.needs_revision = False
            self.revision_target_chapter = 0

    def mark_chapter_status(self, chapter_id: int, status: ChapterStatus) -> None:
        """更新章节计划状态。"""
        for chapter in self.get_all_chapters_flat():
            if chapter.id == chapter_id:
                chapter.status = status
                return

    def mark_section_status(self, section_id: str, status: SectionStatus) -> None:
        """更新三级小节计划状态。"""
        section = self.get_section_plan(section_id)
        if section is not None:
            section.status = status

    def get_planted_foreshadows(self) -> list[ForeshadowItem]:
        """获取已埋入但未回收的伏笔"""
        return [f for f in self.foreshadows if f.status == "planted"]

    def advance_to_next_chapter(self) -> bool:
        """推进到下一章，返回是否还有更多章节"""
        part = self.get_current_part()
        if part is None:
            return False
        if self.current_chapter_idx < len(part.chapters) - 1:
            self.current_chapter_idx += 1
            chapter = self.get_current_chapter()
            self.current_section_id = chapter.sections[0].id if chapter and chapter.sections else ""
            return True
        if self.current_part_idx < len(self.parts) - 1:
            self.current_part_idx += 1
            self.current_chapter_idx = 0
            chapter = self.get_current_chapter()
            self.current_section_id = chapter.sections[0].id if chapter and chapter.sections else ""
            return True
        return False

    def advance_to_next_section(self) -> bool:
        """推进到下一三级写作单元，返回是否还有更多小节。"""
        sections = self.get_all_sections_flat()
        if not sections:
            return False
        current_id = self.current_section_id or sections[0].id
        for index, section in enumerate(sections):
            if section.id != current_id:
                continue
            if index + 1 >= len(sections):
                return False
            return self.set_current_section_by_id(sections[index + 1].id)
        return self.set_current_section_by_id(sections[0].id)

    def get_previous_chapters_summary(self, last_n: int = 3) -> str:
        """获取前 N 章的摘要，用于上下文连贯"""
        recent = self.chapters[-last_n:] if self.chapters else []
        summaries: list[str] = []
        for ch in recent:
            preview = ch.markdown[:500].replace("\n", " ")
            summaries.append(f"第{ch.chapter_id}章 {ch.title}: {preview}...")
        return "\n\n".join(summaries)

    def get_covered_topics(self, exclude_chapter_id: int | None = None) -> str:
        """汇总其他章节已覆盖的标题与要点，供当前章去重。

        全书层面的内容重叠是长文档写作的典型病：相邻主题各自检索到相似资料、
        各自展开，导致重复。把已定稿章节的标题 + key_points 作为「已覆盖清单」
        提供给检索与写作，使当前章主动规避与别章撞车。
        """
        lines: list[str] = []
        for part in self.parts:
            for chapter in part.chapters:
                if chapter.id == exclude_chapter_id:
                    continue
                # 仅纳入已产出正文的章节，避免用未写章节的空要点误导
                if self.get_chapter_content(chapter.id) is None:
                    continue
                points = "；".join(chapter.key_points) if chapter.key_points else ""
                entry = f"- 第{chapter.id}章 {chapter.title}"
                if points:
                    entry += f"：{points}"
                lines.append(entry)
        return "\n".join(lines)
