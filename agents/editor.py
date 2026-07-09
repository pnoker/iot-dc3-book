"""
Editor Agent - 一致性审校 + 伏笔验证
"""

from __future__ import annotations

from typing import Any

from core.state import BookState

from .base import BaseAgent

_EDITOR_SYSTEM = """你是一位严格的技术书籍审校编辑。
你的任务是对已撰写的章节进行专业审校，检查以下维度：

## 审校维度
1. **内容准确性**: 技术概念是否正确，描述是否准确
2. **逻辑连贯性**: 与前文是否衔接自然，论述是否有逻辑跳跃
3. **伏笔完整性**: 伏笔是否已自然植入/回收
4. **前后一致性**: 术语使用、观点立场是否与前文一致
5. **内容充实度**: 是否达到目标字数，是否有实质性内容
6. **结构完整性**: 是否具备自然开篇、主体层次、图表/案例支撑和章节收束；不要要求每章固定引言或练习题

## 伏笔核验
对「本章伏笔任务清单」中的每一条，逐条判定作者是否已在正文中真正完成：
- 埋入类任务：正文是否已自然埋入该伏笔
- 回收类任务：正文是否已对之前埋下的伏笔给出呼应/解答
在 foreshadow_checks 中如实报告每条的 id、类型(plant/resolve)与是否达成(done)。

## 输出格式
```json
{
  "pass": true,
  "overall_score": 8,
  "dimension_scores": {
    "accuracy": 8, "coherence": 8, "foreshadow": 7,
    "consistency": 8, "completeness": 7, "structure": 9
  },
  "foreshadow_checks": [
    {"id": "F001", "type": "plant", "done": true},
    {"id": "F002", "type": "resolve", "done": false}
  ],
  "issues": [
    {"severity": "minor", "dimension": "coherence", "description": "...", "suggestion": "..."}
  ],
  "summary": "总体评价"
}
```

## 判定规则
- 存在 critical 级别问题: pass = false
- overall_score < 6: pass = false
- foreshadow 维度得分 < 5: pass = false
- 存在 type=resolve 且 done=false 的伏笔（应回收却未回收）: pass = false"""


class EditorAgent(BaseAgent):
    """一致性审校 Agent"""

    def review(self, state: BookState) -> dict[str, Any]:
        """审校当前章节，返回审校报告"""
        chapter = state.get_current_chapter()
        content = state.get_chapter_content(chapter.id) if chapter else None
        if not chapter or not content:
            return {"pass": True, "summary": "无内容需要审校"}

        prev_summary = state.get_previous_chapters_summary(last_n=3)
        foreshadow_prompt = self._build_foreshadow_prompt(state)

        # 伏笔检查清单
        foreshadow_checklist: list[str] = []
        for fs in state.foreshadows:
            if fs.planted_chapter == chapter.id:
                foreshadow_checklist.append(f"- 应埋入: {fs.description}")
            if fs.planned_resolve_chapter == chapter.id and fs.status == "planted":
                foreshadow_checklist.append(f"- 应回收: {fs.description}")
        checklist_str = "\n".join(foreshadow_checklist) if foreshadow_checklist else "本章无特定伏笔任务。"

        user_prompt = f"""请审校以下章节：

# 章节信息
- 第{chapter.id}章 {chapter.title}
- 目标字数: {state.style.target_words_per_chapter}
- 实际字数: {content.word_count}字

# 本章伏笔任务清单
{checklist_str}

# 前文摘要
{prev_summary if prev_summary else "第一章，无前文。"}

{foreshadow_prompt}

# 章节正文
{content.markdown}

请进行严格审校并输出 JSON 格式报告。"""

        self.logger.info("审校第%d章...", chapter.id)
        try:
            return self.llm.chat_json(_EDITOR_SYSTEM, user_prompt, temperature=0.3)
        except ValueError as exc:
            self.logger.error("审校报告解析失败")
            raise RuntimeError("审校报告解析失败，已阻断章节质量门。") from exc
