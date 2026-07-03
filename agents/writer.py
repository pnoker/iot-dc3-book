"""
Writer Agent - 逐章写作与修改
"""

from __future__ import annotations

from core.state import BookState
from .base import BaseAgent

_WRITER_SYSTEM = """你是一位资深的物联网技术书籍作者。
你的任务是根据详细大纲和参考资料，撰写高质量的技术书籍章节。

## 写作原则
1. 内容专业准确，参考资料需融合改写，不能直接复制
2. 语言通俗易懂，面向工程师和高校师生
3. 适当使用示例、类比来解释复杂概念
4. 按照指定的章节结构撰写（引言 → 正文分节 → 本章小结 → 思考与练习）
5. 在合适的地方埋入或回收伏笔，使全书前后呼应
6. 严格遵守格式规范和术语规范

## 输出要求
- 输出完整的 Markdown 格式章节正文
- 使用正确的标题层级（# ## ### ####）
- 不要输出章节编号以外的元信息
- 确保内容充实，达到目标字数"""


class WriterAgent(BaseAgent):
    """章节写作 Agent"""

    def write(self, state: BookState) -> str:
        """为当前章节撰写正文"""
        chapter = state.get_current_chapter()
        part = state.get_current_part()
        if not chapter or not part:
            return ""

        prev_summary = state.get_previous_chapters_summary(last_n=2)
        style_prompt = self._build_style_prompt(state.style)
        foreshadow_prompt = self._build_foreshadow_prompt(state)
        ref_prompt = self._build_references_prompt(state)
        covered = state.get_covered_topics(exclude_chapter_id=chapter.id)
        dedup_prompt = (
            f"\n## 其他章节已覆盖内容（本章勿重复展开，如需提及请一句带过并指向对应章节）\n{covered}"
            if covered
            else ""
        )

        # 伏笔任务
        foreshadow_hints: list[str] = []
        for fs in state.foreshadows:
            if fs.planted_chapter == chapter.id and fs.status == "planted":
                foreshadow_hints.append(f"- 请在本章适当位置埋入伏笔: {fs.description}")
            if fs.planned_resolve_chapter == chapter.id and fs.status == "planted":
                foreshadow_hints.append(f"- 请在本章回收之前埋下的伏笔: {fs.description}")
        foreshadow_instruction = "\n## 本章伏笔任务\n" + "\n".join(foreshadow_hints) if foreshadow_hints else ""

        user_prompt = f"""请撰写以下章节：

# 章节信息
- 篇: {part.name}
- 章节: 第{chapter.id}章 {chapter.title}
- 编号前缀: {part.prefix}
- 概述: {chapter.summary}

# 详细大纲
{chapter.outline}

# 核心要点
{chr(10).join(f"- {p}" for p in chapter.key_points)}

{ref_prompt}

{foreshadow_prompt}

{foreshadow_instruction}

# 前文摘要（保持连贯性）
{prev_summary if prev_summary else "这是全书第一章，无需前文。"}
{dedup_prompt}

{style_prompt}

请开始撰写完整的章节正文。"""

        self.logger.info("撰写第%d章 %s...", chapter.id, chapter.title)
        return self.llm.chat(_WRITER_SYSTEM, user_prompt, temperature=0.8, max_tokens=16384)

    def revise(self, state: BookState, feedback: str) -> str:
        """根据审校反馈修改章节"""
        chapter = state.get_current_chapter()
        content = state.get_chapter_content(chapter.id) if chapter else None
        if not chapter or not content:
            return ""

        style_prompt = self._build_style_prompt(state.style)
        user_prompt = f"""请根据以下审校反馈修改第{chapter.id}章 {chapter.title}。

# 审校反馈
{feedback}

# 当前正文
{content.markdown}

{style_prompt}

请输出修改后的完整章节正文（Markdown 格式）。"""

        self.logger.info("修改第%d章...", chapter.id)
        return self.llm.chat(_WRITER_SYSTEM, user_prompt, temperature=0.7, max_tokens=16384)
