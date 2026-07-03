from __future__ import annotations

from typing import Any

from agents.research import ResearchAgent
from agents.writer import WriterAgent
from core.state import BookState, ChapterContent, ChapterPlan, PartPlan, ReferenceChunk


def _state_two_chapters() -> BookState:
    return BookState(
        parts=[
            PartPlan(
                name="基础篇",
                prefix="一",
                chapters=[
                    ChapterPlan(id=1, title="物联网概述", summary="概述", key_points=["连接", "感知"]),
                    ChapterPlan(id=2, title="通信协议", summary="协议", key_points=["MQTT", "CoAP"]),
                ],
            )
        ]
    )


def test_get_covered_topics_lists_only_written_other_chapters() -> None:
    state = _state_two_chapters()
    state.current_chapter_idx = 1  # 当前在第 2 章
    # 仅第 1 章已产出正文
    state.chapters.append(ChapterContent(chapter_id=1, title="物联网概述", markdown="# 正文"))

    covered = state.get_covered_topics(exclude_chapter_id=2)

    assert "第1章 物联网概述" in covered
    assert "连接" in covered
    assert "第2章" not in covered  # 排除当前章


def test_get_covered_topics_excludes_unwritten_chapters() -> None:
    state = _state_two_chapters()
    # 无任何章节写完 → 空（不能用未写章节的空要点误导）
    assert state.get_covered_topics(exclude_chapter_id=1) == ""


class _CapturingLLM:
    def __init__(self) -> None:
        self.user_prompt = ""

    def chat(self, system: str, user: str, temperature: float | None = None, max_tokens: int | None = None) -> str:
        self.user_prompt = user
        return "# 正文\n\n内容"


class _StubRAG:
    def retrieve(self, query: str, top_k: int = 5, *, categories: Any = None, **_: Any) -> list[ReferenceChunk]:
        return []


def test_writer_injects_covered_topics_as_dedup_constraint() -> None:
    state = _state_two_chapters()
    state.current_chapter_idx = 1
    state.chapters.append(ChapterContent(chapter_id=1, title="物联网概述", markdown="# 正文"))
    llm = _CapturingLLM()

    WriterAgent(llm).write(state)

    assert "其他章节已覆盖内容" in llm.user_prompt
    assert "第1章 物联网概述" in llm.user_prompt


def test_research_query_gen_receives_dedup_hint() -> None:
    state = _state_two_chapters()
    state.current_chapter_idx = 1
    state.chapters.append(ChapterContent(chapter_id=1, title="物联网概述", markdown="# 正文"))
    llm = _CapturingLLM()

    ResearchAgent(llm, _StubRAG()).search(state)

    assert "已在其他章节覆盖" in llm.user_prompt
    assert "第1章 物联网概述" in llm.user_prompt
