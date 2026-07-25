"""
Fact Checker Agent - 基于独立检索证据的事实核查

核查依据必须独立于作者用过的资料：若沿用 Writer 的 reference_chunks，等于「用喂给作者的
资料核查作者写的内容」，作者没写进去的错误事实在核查集里也没有对应资料能反驳，构成自证循环。
本 Agent 自持 RAG，从作者实际写出的章节结构（标题 / 小节标题 / 概述）出发二次检索证据。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from core.state import BookState, ReferenceChunk

from .base import BaseAgent

if TYPE_CHECKING:
    from collections.abc import Sequence

    from core.rag import RAGEngine

_FACT_CHECKER_SYSTEM = """你是一位严格的技术事实核查编辑。
你的任务是依据章节正文和「独立检索证据」，检查技术事实、年份、标准、产品能力、架构描述是否有依据。

## 核查原则
1. 优先检查容易误导读者的硬事实：协议能力、标准名称、版本、年份分界、时延/吞吐/成本/市场金额、性能结论、工程实践结论
2. 独立检索证据是核查依据，不是作者的参考资料；对与证据冲突的断言必须提出修订
3. 对没有证据支撑、也非常识性技术知识的重要断言提出修订建议
4. 不要求逐句引用，但关键事实必须能被证据或常识性技术知识支撑
5. 不负责文风和格式，这些交给 Style Guard
6. 对没有证据的精确数字，不要建议“补一个来源”；应建议删除数字、改为定性表达，或标注为假设/示意场景
7. 不要因为正文中的 [S]/[W] 编号未出现在独立证据列表而报错；引用编号由 Citation Guard 单独审核

## 输出格式
```json
{
  "pass": true,
  "score": 8,
  "claims": [
    {"claim": "被核查的关键断言", "status": "supported", "evidence": "依据摘要"}
  ],
  "issues": [
    {"severity": "major", "section_id": "1.1.1", "description": "问题", "suggestion": "修改建议"}
  ],
  "summary": "总体事实核查结论"
}
```

## 判定规则
- 存在 major 或 critical 事实问题时 pass = false
- score < 7 时 pass = false
- issue 能定位到三级小节时必须填写 section_id；不能定位时 section_id 留空字符串"""

# 对抗式复核视角：每票聚焦一类硬事实错误模式，覆盖互不重叠。
_PERSPECTIVES: list[tuple[str, str]] = [
    ("数字/版本/年份分界", "重点审查精确数字、版本号、标准版本、年份分界与时间线；这类断言最易出错且最误导读者。"),
    ("架构/协议/标准断言", "重点审查协议能力、架构描述、标准名称与状态、产品能力边界是否与证据一致。"),
    ("性能/成本/市场结论", "重点审查时延/吞吐/成本/市场金额/占比等量化结论，以及由其推出的工程实践结论是否有依据。"),
]

_HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$", re.MULTILINE)
_MAX_EVIDENCE_QUERIES = 12


class FactCheckerAgent(BaseAgent):
    """事实核查 Agent（自持 RAG 做独立取证）"""

    def __init__(self, llm: object, rag: RAGEngine, query_categories: Sequence[str] | None = None) -> None:
        super().__init__(llm)  # type: ignore[arg-type]
        self.rag = rag
        self.query_categories = list(query_categories) if query_categories else None

    def check(self, state: BookState) -> dict[str, Any]:
        """核查当前章节事实准确性。"""
        chapter = state.get_current_chapter()
        content = state.get_chapter_content(chapter.id) if chapter else None
        if not chapter or not content:
            return {"pass": True, "score": 10, "claims": [], "issues": [], "summary": "无内容需要核查"}

        evidence = self._gather_evidence(chapter.title, chapter.summary, content.markdown)
        evidence_prompt = self._build_evidence_prompt(evidence)
        user_prompt = f"""请核查以下章节的技术事实准确性。

# 章节信息
- 第{chapter.id}章 {chapter.title}
- 概述: {chapter.summary}

{evidence_prompt}

# 章节正文
{content.markdown}

请输出严格 JSON。"""

        self.logger.info("事实核查第%d章（独立取证 %d 段）...", chapter.id, len(evidence))
        try:
            return self._adversarial_vote(
                _FACT_CHECKER_SYSTEM,
                user_prompt,
                _PERSPECTIVES,
                temperature=0.2,
                enabled=state.quality.adversarial_review_enabled,
            )
        except ValueError as exc:
            self.logger.error("事实核查报告解析失败")
            raise RuntimeError("事实核查报告解析失败，已阻断章节质量门。") from exc

    def _gather_evidence(self, title: str, summary: str, markdown: str) -> list[ReferenceChunk]:
        """从作者实际写出的结构（标题 + 小节标题 + 概述）出发独立检索证据并去重。"""
        queries = self._evidence_queries(title, summary, markdown)
        evidence: list[ReferenceChunk] = []
        additional: list[ReferenceChunk] = []
        seen: set[str] = set()
        for query in queries:
            if not query.strip():
                continue
            query_hits: list[ReferenceChunk] = []
            for chunk in self.rag.retrieve(query, top_k=4, categories=self.query_categories):
                if chunk.text not in seen:
                    seen.add(chunk.text)
                    query_hits.append(chunk)
            if query_hits:
                evidence.append(query_hits[0])
                additional.extend(query_hits[1:])
        if len(evidence) >= 12:
            return evidence[:12]
        additional.sort(key=lambda chunk: chunk.relevance_score, reverse=True)
        return [*evidence, *additional[: 12 - len(evidence)]]

    @staticmethod
    def _evidence_queries(title: str, summary: str, markdown: str) -> list[str]:
        """优先覆盖全部 H2，再用均匀采样的 H3 补足查询预算。"""
        secondary: list[str] = []
        tertiary: list[str] = []
        for heading in _HEADING_RE.finditer(markdown):
            level = len(heading.group("marks"))
            heading_title = heading.group("title")
            if level == 2:
                secondary.append(heading_title)
            elif level == 3:
                tertiary.append(heading_title)

        chapter_query = f"{title} {summary}".strip()
        heading_budget = _MAX_EVIDENCE_QUERIES - int(bool(chapter_query))
        selected_secondary = _sample_evenly(secondary, heading_budget)
        remaining = heading_budget - len(selected_secondary)
        selected_tertiary = _sample_evenly(tertiary, remaining)
        return list(dict.fromkeys([chapter_query, *selected_secondary, *selected_tertiary]))

    @staticmethod
    def _build_evidence_prompt(evidence: list[ReferenceChunk]) -> str:
        """组装独立检索证据提示词。"""
        if not evidence:
            return "## 独立检索证据\n未检索到相关证据，请依据常识性技术知识核查。"
        lines = ["## 独立检索证据（核查依据，非作者参考资料）"]
        for i, ref in enumerate(evidence, 1):
            lines.append(f"### 证据 {i}: {ref.source_file} - {ref.chapter_or_section}")
            lines.append(ref.text[:500])
            lines.append("")
        return "\n".join(lines)


def _sample_evenly(values: list[str], limit: int) -> list[str]:
    if limit <= 0 or not values:
        return []
    if len(values) <= limit:
        return values
    if limit == 1:
        return [values[-1]]
    indexes = [round(index * (len(values) - 1) / (limit - 1)) for index in range(limit)]
    return [values[index] for index in indexes]
