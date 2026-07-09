"""Citation Guard Agent - 引用和断言守门。"""

from __future__ import annotations

from typing import Any

from core.state import BookState

from .base import BaseAgent

_CITATION_GUARD_SYSTEM = """你是一位技术图书事实与引用编辑。
请检查章节中的版本号、统计数字、行业趋势、项目能力描述是否有明确依据。
对缺少依据的重要断言必须要求修订。输出严格 JSON。

判定要点：
- 正文写了来源名称，但研究资料包没有该来源或对应内容，仍视为缺少依据。
- 研究资料包中 [S] 表示本地知识库证据，[W] 表示显式 URL 在线证据；关键硬事实应能对应到这些编号。
- 真实项目案例、成本、比例、性能、市场规模、年份分界、标准状态必须能对应到资料包。
- 没有证据时，建议必须具体到“删除数字”“改为定性表述”或“标注为假设场景并移除精确数据”。"""

# 对抗式复核视角：每票聚焦一类引用/断言缺依据的模式。
_PERSPECTIVES: list[tuple[str, str]] = [
    ("硬数据溯源", "重点审查版本号、统计数字、性能与成本数据能否对应到研究资料包中的 [S]/[W] 编号。"),
    ("项目/案例真实性", "重点审查真实项目案例、企业名称、落地成本与规模描述是否有资料支撑，警惕虚构或夸大。"),
    ("趋势/市场断言", "重点审查行业趋势、市场规模、占比、增长率等宏观断言是否有据，警惕无来源的想当然结论。"),
]


class CitationGuardAgent(BaseAgent):
    """引用守门 Agent。"""

    def check(self, state: BookState) -> dict[str, Any]:
        chapter = state.get_current_chapter()
        content = state.get_chapter_content(chapter.id) if chapter else None
        if not chapter or not content:
            return {"pass": True, "issues": []}
        dossier = chapter.research_dossier.model_dump(mode="python") if chapter.research_dossier else {}
        user_prompt = f"""请检查章节引用与关键断言。

# 章节
第{chapter.id}章 {chapter.title}

# 研究资料包
{dossier}

# 正文
{content.markdown}

请输出 JSON：{{"pass": true, "issues": [{{"severity": "major", "section_id": "1.1.1", "claim": "...", "suggestion": "..."}}], "summary": "..."}}。
issue 能定位到三级小节时必须填写 section_id；不能定位时 section_id 留空字符串。"""
        self.logger.info("引用守门检查第%d章...", chapter.id)
        try:
            return self._adversarial_vote(
                _CITATION_GUARD_SYSTEM,
                user_prompt,
                _PERSPECTIVES,
                temperature=0.2,
                enabled=state.quality.adversarial_review_enabled,
            )
        except ValueError as exc:
            self.logger.error("引用检查报告解析失败")
            raise RuntimeError("引用检查报告解析失败，已阻断章节质量门。") from exc
