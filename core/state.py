"""
核心状态定义 - 所有 Agent 共享的数据结构
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ChapterStatus = Literal["pending", "researched", "written", "fact_checked", "styled", "reviewed", "approved"]


class StyleConfig(BaseModel):
    """写作风格配置"""

    tone: str = ""
    perspective: str = "第三人称"
    terminology_rule: str = ""
    forbidden_words: list[str] = Field(default_factory=list)
    chapter_structure: list[str] = Field(default_factory=list)
    target_words_per_chapter: str = "4000-8000字"
    format_rules: dict[str, str] = Field(default_factory=dict)


class ChapterPlan(BaseModel):
    """单章规划"""

    id: int
    title: str
    summary: str = ""
    outline: str = ""  # 详细大纲（Planner 生成）
    key_points: list[str] = Field(default_factory=list)
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
    revision_count: int = 0
    # Editor 对本章伏笔任务的核验结论 [{id, type, done}]，供质量门通过时转移伏笔状态
    foreshadow_checks: list[dict[str, Any]] = Field(default_factory=list)


class ReferenceChunk(BaseModel):
    """参考书籍检索结果"""

    source_file: str
    chapter_or_section: str
    text: str
    relevance_score: float = 0.0


class BookState(BaseModel):
    """
    LangGraph 全局状态 - 所有 Agent 读写此状态。

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

    # --- 已完成内容 ---
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

    def get_chapter_content(self, chapter_id: int) -> ChapterContent | None:
        """按 ID 获取已写章节内容"""
        for ch in self.chapters:
            if ch.chapter_id == chapter_id:
                return ch
        return None

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
                    return True
        return False

    def clear_chapter_feedback(self, chapter_id: int) -> None:
        """清空指定章节的质量反馈和修订标记。"""
        content = self.get_chapter_content(chapter_id)
        if content:
            content.review_feedback = ""
            content.style_feedback = ""
            content.fact_feedback = ""
        if self.revision_target_chapter in (0, chapter_id):
            self.needs_revision = False
            self.revision_target_chapter = 0

    def mark_chapter_status(self, chapter_id: int, status: ChapterStatus) -> None:
        """更新章节计划状态。"""
        for chapter in self.get_all_chapters_flat():
            if chapter.id == chapter_id:
                chapter.status = status
                return

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
            return True
        if self.current_part_idx < len(self.parts) - 1:
            self.current_part_idx += 1
            self.current_chapter_idx = 0
            return True
        return False

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
