"""
Style Guard Agent - 风格与格式校验
"""

from __future__ import annotations

from typing import Any

from core.state import BookState

from .base import BaseAgent

_STYLE_GUARD_SYSTEM = """你是一位书籍排版与风格规范专家。
你的任务是对章节正文进行风格和格式校验。

## 校验维度
1. 标题层级: 是否正确使用了 # ## ### #### 层级
2. 术语规范: 专业术语首次出现是否附英文原文
3. 禁用词汇: 是否包含指定的禁用词汇
4. 段落结构: 段落是否过长或过短
5. 图表编号: 图表是否按规范编号
6. 图表规格: `book-figure` 是否包含类型、图例、元素、关系、图注和渲染说明，且没有被替换成 Markdown 图片占位、Mermaid、SVG、HTML 或 ASCII 图
7. 代码块: 是否正确标注语言；`book-figure` 代码块是图表规格，不按代码示例扣分
8. 章节结构: 是否自然、层次清晰、收束完整；不要因为缺少固定“引言”或“思考与练习”而判失败

## 输出格式
```json
{
  "pass": true,
  "score": 8,
  "issues": [
    {"type": "forbidden_word", "section_id": "1.1.1", "line_hint": "第3段", "description": "...", "fix": "..."}
  ],
  "statistics": {
    "word_count": 5000,
    "heading_count": {"#": 1, "##": 3, "###": 5},
    "figure_count": 2,
    "table_count": 1,
    "code_block_count": 3
  }
}
```
score < 6 时 pass = false。
issue 能定位到三级小节时必须填写 section_id；不能定位时 section_id 留空字符串。"""

# 对抗式复核视角：每票聚焦一类风格/格式问题。
_PERSPECTIVES: list[tuple[str, str]] = [
    ("标题层级与章节结构", "重点审查 # ## ### #### 层级是否规范、层次是否清晰、章节是否自然收束。"),
    ("术语规范与禁用词", "重点审查专业术语首次出现是否附英文原文、术语是否统一、是否包含禁用词汇。"),
    ("图表规格与代码块", "重点审查 book-figure 规格块字段是否完整、是否被替换成图片占位/Mermaid/SVG/HTML/ASCII，以及代码块语言标注。"),
]


class StyleGuardAgent(BaseAgent):
    """风格格式校验 Agent"""

    def check(self, state: BookState) -> dict[str, Any]:
        """校验当前章节的风格和格式"""
        chapter = state.get_current_chapter()
        content = state.get_chapter_content(chapter.id) if chapter else None
        if not chapter or not content:
            return {"pass": True, "score": 10, "issues": [], "statistics": {}}

        style_prompt = self._build_style_prompt(state.style)

        # 预检查
        precheck_issues: list[str] = []
        for word in state.style.forbidden_words:
            if word in content.markdown:
                precheck_issues.append(f"发现禁用词汇: '{word}'")

        user_prompt = f"""请校验以下章节的风格和格式：

{style_prompt}

# 章节正文
{content.markdown}

# 预检查结果
{chr(10).join(precheck_issues) if precheck_issues else "预检查通过。"}

请进行完整校验并输出 JSON 格式报告。"""

        self.logger.info("校验第%d章风格...", chapter.id)
        try:
            return self._adversarial_vote(
                _STYLE_GUARD_SYSTEM,
                user_prompt,
                _PERSPECTIVES,
                temperature=0.2,
                enabled=state.quality.adversarial_review_enabled,
            )
        except ValueError as exc:
            self.logger.error("风格校验报告解析失败")
            raise RuntimeError("风格校验报告解析失败，已阻断章节质量门。") from exc
