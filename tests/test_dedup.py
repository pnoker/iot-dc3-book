from __future__ import annotations

from typing import Any

from agents.research import ResearchAgent
from agents.writer import WriterAgent
from core.state import BookState, ChapterContent, ChapterPlan, PartPlan, ReferenceChunk
from core.web_research import WebEvidence


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


def test_research_dossier_uses_numbered_local_and_web_evidence(monkeypatch: Any) -> None:
    state = _state_two_chapters()
    chunk = ReferenceChunk(
        source_file="books/iot.pdf",
        chapter_or_section="第1节",
        text="物联网通过传感器、网络和平台连接物理世界。",
        relevance_score=0.9,
    )

    def fake_fetch(urls: list[str], timeout_seconds: float, max_chars_per_url: int) -> list[WebEvidence]:
        assert urls == ["https://example.test/report"]
        assert timeout_seconds == 3
        assert max_chars_per_url == 100
        return [WebEvidence(url=urls[0], title="Report", excerpt="在线报告摘录")]

    monkeypatch.setattr("agents.research.fetch_web_evidence", fake_fetch)
    agent = ResearchAgent(
        _CapturingLLM(),
        _StubRAG(),
        web_enabled=True,
        web_urls=["https://example.test/report"],
        web_timeout_seconds=3,
        web_max_chars_per_url=100,
    )

    dossier = agent.build_dossier(state, [chunk])

    assert dossier is not None
    assert [note.id for note in dossier.evidence_notes] == ["S1", "W1"]
    assert "[S1] books/iot.pdf" in dossier.source_notes[0]
    assert "[W1] Report" in dossier.web_notes[0]
    assert "[S]/[W]" in dossier.evidence_policy
