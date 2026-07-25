from __future__ import annotations

from typing import Any

from agents.fact_checker import FactCheckerAgent
from core.state import BookState, ChapterContent, ChapterPlan, PartPlan, ReferenceChunk


class _RecordingRAG:
    """记录检索查询，返回固定证据。"""

    def __init__(self) -> None:
        self.queries: list[str] = []

    def retrieve(self, query: str, top_k: int = 5, *, categories: Any = None, **_: Any) -> list[ReferenceChunk]:
        self.queries.append(query)
        return [
            ReferenceChunk(
                source_file="books/x.pdf", chapter_or_section="协议", text=f"证据:{query}", relevance_score=1.0
            )
        ]


class _CapturingLLM:
    def __init__(self) -> None:
        self.user_prompt = ""

    def chat_json(self, system: str, user: str, temperature: float | None = None) -> dict[str, Any]:
        self.user_prompt = user
        return {"pass": True, "score": 9, "claims": [], "issues": [], "summary": "ok"}


def _state() -> BookState:
    state = BookState(
        parts=[PartPlan(name="基础篇", prefix="一", chapters=[ChapterPlan(id=1, title="物联网概述", summary="概述")])]
    )
    state.chapters.append(
        ChapterContent(
            chapter_id=1,
            title="物联网概述",
            markdown="# 第一章\n\n## 一.1 感知层\nModbus 是主从协议。\n\n## 一.2 网络层\nNB-IoT 低功耗。",
        )
    )
    return state


def test_fact_checker_retrieves_independent_evidence_from_chapter_structure() -> None:
    rag = _RecordingRAG()
    checker = FactCheckerAgent(_CapturingLLM(), rag)

    checker.check(_state())

    # 检索查询来自作者实际写出的标题/小节，而非 state.reference_chunks
    assert any("感知层" in q for q in rag.queries)
    assert any("网络层" in q for q in rag.queries)
    assert any("物联网概述" in q for q in rag.queries)


def test_fact_checker_retrieves_evidence_for_late_secondary_heading() -> None:
    state = _state()
    state.chapters[0].markdown = (
        "# 第一章\n\n"
        + "\n\n".join(f"## 1.{index} 主题{index}\n正文。" for index in range(1, 8))
        + "\n\n## 1.8 MCP 协议\n正文。"
    )
    rag = _RecordingRAG()

    FactCheckerAgent(_CapturingLLM(), rag).check(state)

    assert any("MCP 协议" in query for query in rag.queries)


def test_fact_checker_feeds_retrieved_evidence_not_state_reference_chunks() -> None:
    rag = _RecordingRAG()
    llm = _CapturingLLM()
    state = _state()
    # 故意在 state 里放入与本章无关的旧参考，验证核查不再依赖它
    state.reference_chunks = [
        ReferenceChunk(source_file="stale.md", chapter_or_section="旧", text="旧的作者参考资料", relevance_score=1.0)
    ]

    FactCheckerAgent(llm, rag).check(state)

    assert "独立检索证据" in llm.user_prompt
    assert "旧的作者参考资料" not in llm.user_prompt  # 不再喂作者用过的同一批资料


def test_fact_checker_no_content_passes_without_retrieval() -> None:
    rag = _RecordingRAG()
    state = BookState(
        parts=[PartPlan(name="基础篇", prefix="一", chapters=[ChapterPlan(id=1, title="概述", summary="")])]
    )

    result = FactCheckerAgent(_CapturingLLM(), rag).check(state)

    assert result["pass"] is True
    assert rag.queries == []  # 无正文不检索
