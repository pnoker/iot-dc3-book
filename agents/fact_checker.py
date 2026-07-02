"""
Fact Checker Agent - 基于参考资料的事实核查
"""

from __future__ import annotations

from typing import Any

from core.state import BookState

from .base import BaseAgent

_FACT_CHECKER_SYSTEM = """你是一位严格的技术事实核查编辑。
你的任务是依据章节正文和参考资料，检查技术事实、年份、标准、产品能力、架构描述是否有依据。

## 核查原则
1. 优先检查容易误导读者的硬事实：协议能力、标准名称、版本、性能结论、工程实践结论
2. 对没有参考资料支撑的重要断言提出修订建议
3. 不要求逐句引用，但关键事实必须能被参考资料或常识性技术知识支撑
4. 不负责文风和格式，这些交给 Style Guard

## 输出格式
```json
{
  "pass": true,
  "score": 8,
  "claims": [
    {"claim": "被核查的关键断言", "status": "supported", "evidence": "依据摘要"}
  ],
  "issues": [
    {"severity": "major", "description": "问题", "suggestion": "修改建议"}
  ],
  "summary": "总体事实核查结论"
}
```

## 判定规则
- 存在 major 或 critical 事实问题时 pass = false
- score < 7 时 pass = false"""


class FactCheckerAgent(BaseAgent):
    """事实核查 Agent"""

    def check(self, state: BookState) -> dict[str, Any]:
        """核查当前章节事实准确性。"""
        chapter = state.get_current_chapter()
        content = state.get_chapter_content(chapter.id) if chapter else None
        if not chapter or not content:
            return {"pass": True, "score": 10, "claims": [], "issues": [], "summary": "无内容需要核查"}

        ref_prompt = self._build_references_prompt(state)
        user_prompt = f"""请核查以下章节的技术事实准确性。

# 章节信息
- 第{chapter.id}章 {chapter.title}
- 概述: {chapter.summary}

{ref_prompt}

# 章节正文
{content.markdown}

请输出严格 JSON。"""

        self.logger.info("事实核查第%d章...", chapter.id)
        try:
            return self.llm.chat_json(_FACT_CHECKER_SYSTEM, user_prompt, temperature=0.2)
        except ValueError:
            self.logger.error("事实核查报告解析失败")
            return {
                "pass": False,
                "score": 5,
                "claims": [],
                "issues": [{"severity": "major", "description": "事实核查报告解析失败", "suggestion": "重新核查"}],
                "summary": "事实核查解析失败",
            }
