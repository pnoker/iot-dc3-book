"""
Director Agent - 终审 + 输出生成
"""

from __future__ import annotations

from typing import Any

from core.state import BookState

from .base import BaseAgent

_DIRECTOR_SYSTEM = """你是一位资深的书籍总编辑。
你的任务是对全书进行终审，评估整体质量并生成最终报告。

## 终审维度
1. 全书一致性: 术语、风格、立场是否全书统一
2. 逻辑递进: 基础→技术→应用的知识递进是否合理
3. 伏笔回收: 所有伏笔是否已回收或合理放弃
4. 章节衔接: 篇章之间的过渡是否自然
5. 内容覆盖: 物联网核心知识是否覆盖完整
6. 实用价值: 对读者是否有实际指导意义

## 输出格式
```json
{
  "pass": true,
  "overall_score": 8,
  "dimension_scores": {
    "consistency": 8, "progression": 8, "foreshadow": 7,
    "cohesion": 8, "coverage": 8, "practicality": 8
  },
  "chapter_reviews": [
    {"chapter_id": 1, "score": 8, "highlights": "...", "issues": "..."}
  ],
  "unresolved_foreshadows": [],
  "suggestions": ["..."],
  "summary": "终审总结"
}
```"""


class DirectorAgent(BaseAgent):
    """终审 Agent"""

    def final_review(self, state: BookState) -> dict[str, Any]:
        """全书终审"""
        chapters_overview: list[str] = []
        for ch in state.chapters:
            preview = ch.markdown[:300].replace("\n", " ")
            chapters_overview.append(f"第{ch.chapter_id}章 {ch.title} ({ch.word_count}字)\n开头: {preview}...")

        foreshadow_status: list[str] = []
        for fs in state.foreshadows:
            foreshadow_status.append(
                f"- [{fs.status}] {fs.id}: {fs.description} (第{fs.planted_chapter}章→第{fs.planned_resolve_chapter}章)"
            )

        user_prompt = f"""请对全书进行终审：

# 书籍信息
- 书名: {state.book_title}
- 共 {len(state.chapters)} 章

# 各章摘要
{chr(10).join(chapters_overview)}

# 伏笔状态
{chr(10).join(foreshadow_status) if foreshadow_status else "无伏笔"}

请输出 JSON 格式的终审报告。"""

        self.logger.info("全书终审中...")
        try:
            return self.llm.chat_json(_DIRECTOR_SYSTEM, user_prompt, temperature=0.3)
        except ValueError:
            self.logger.error("终审报告解析失败")
            return {"pass": False, "overall_score": 5, "summary": "终审报告解析失败"}
