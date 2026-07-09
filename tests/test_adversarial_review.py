from __future__ import annotations

from typing import Any

from agents.base import BaseAgent
from agents.editor import EditorAgent, _aggregate_foreshadow_checks
from agents.fact_checker import FactCheckerAgent
from core.state import BookState, ChapterContent, ChapterPlan, PartPlan, ReferenceChunk


class _CountingLLM:
    """记录每次 chat_json 的 system 提示，返回可配置的报告序列。"""

    def __init__(self, reports: list[dict[str, Any]]) -> None:
        self._reports = reports
        self.systems: list[str] = []
        self.calls = 0

    def chat_json(self, system: str, user: str, temperature: float | None = None) -> dict[str, Any]:
        self.systems.append(system)
        report = self._reports[self.calls % len(self._reports)]
        self.calls += 1
        return report


class _RecordingRAG:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def retrieve(self, query: str, top_k: int = 5, *, categories: Any = None, **_: Any) -> list[ReferenceChunk]:
        self.queries.append(query)
        return [ReferenceChunk(source_file="x.pdf", chapter_or_section="s", text=f"证据:{query}", relevance_score=1.0)]


def _state(*, adversarial: bool) -> BookState:
    state = BookState(
        parts=[PartPlan(name="基础篇", prefix="一", chapters=[ChapterPlan(id=1, title="物联网概述", summary="概述")])]
    )
    state.chapters.append(
        ChapterContent(chapter_id=1, title="物联网概述", markdown="# 第一章\n\n## 一.1 感知层\nModbus 是主从协议。")
    )
    state.quality.adversarial_review_enabled = adversarial
    return state


# ---- 聚合规则 ----


def test_aggregate_majority_fail() -> None:
    result = BaseAgent._aggregate_votes(
        [
            {"pass": False, "issues": [{"description": "错1"}], "score": 4},
            {"pass": False, "issues": [{"description": "错1"}], "score": 6},
            {"pass": True, "issues": [], "score": 9},
        ]
    )
    assert result["pass"] is False
    assert result["issues"] == [{"description": "错1"}]  # 重复 issue 已去重
    assert result["score"] == 4  # 取最小值（保守）


def test_aggregate_majority_pass() -> None:
    result = BaseAgent._aggregate_votes([{"pass": False}, {"pass": True}, {"pass": True}])
    assert result["pass"] is True


def test_aggregate_merges_claims() -> None:
    result = BaseAgent._aggregate_votes(
        [
            {"pass": True, "claims": [{"claim": "A"}]},
            {"pass": True, "claims": [{"claim": "A"}, {"claim": "B"}]},
        ]
    )
    assert result["claims"] == [{"claim": "A"}, {"claim": "B"}]


# ---- 退化与视角数 ----


def test_disabled_falls_back_to_single_call() -> None:
    rag = _RecordingRAG()
    llm = _CountingLLM([{"pass": True, "score": 9, "issues": [], "summary": "ok"}])
    FactCheckerAgent(llm, rag).check(_state(adversarial=False))
    assert llm.calls == 1  # 未开启对抗时退化为单次自评


def test_enabled_runs_three_perspectives_with_distinct_systems() -> None:
    rag = _RecordingRAG()
    llm = _CountingLLM([{"pass": True, "score": 9, "issues": [], "summary": "ok"}])
    FactCheckerAgent(llm, rag).check(_state(adversarial=True))
    assert llm.calls == 3  # 三视角各判定一次
    assert len(set(llm.systems)) == 3  # 三次 system 提示互不相同（视角分化）


def test_retrieval_not_amplified_by_voting() -> None:
    """独立取证在投票之前完成，检索次数不随视角数放大。"""
    rag_off = _RecordingRAG()
    FactCheckerAgent(_CountingLLM([{"pass": True}]), rag_off).check(_state(adversarial=False))
    rag_on = _RecordingRAG()
    FactCheckerAgent(_CountingLLM([{"pass": True}]), rag_on).check(_state(adversarial=True))
    assert rag_on.queries == rag_off.queries  # 开启对抗不改变检索行为


# ---- editor 伏笔聚合 ----


def test_foreshadow_majority_done() -> None:
    checks = _aggregate_foreshadow_checks(
        [
            {"foreshadow_checks": [{"id": "F1", "type": "resolve", "done": True}]},
            {"foreshadow_checks": [{"id": "F1", "type": "resolve", "done": True}]},
            {"foreshadow_checks": [{"id": "F1", "type": "resolve", "done": False}]},
        ]
    )
    assert checks == [{"id": "F1", "type": "resolve", "done": True}]  # 2:1 多数判 done


def test_foreshadow_minority_done() -> None:
    checks = _aggregate_foreshadow_checks(
        [
            {"foreshadow_checks": [{"id": "F1", "type": "plant", "done": True}]},
            {"foreshadow_checks": [{"id": "F1", "type": "plant", "done": False}]},
            {"foreshadow_checks": [{"id": "F1", "type": "plant", "done": False}]},
        ]
    )
    assert checks == [{"id": "F1", "type": "plant", "done": False}]  # 1:2 少数不算 done


def test_editor_aggregate_includes_foreshadow_checks() -> None:
    agent = EditorAgent(_CountingLLM([{"pass": True}]))
    result = agent._aggregate_votes(
        [
            {"pass": True, "foreshadow_checks": [{"id": "F1", "type": "resolve", "done": True}]},
            {"pass": True, "foreshadow_checks": [{"id": "F1", "type": "resolve", "done": True}]},
        ]
    )
    assert result["foreshadow_checks"] == [{"id": "F1", "type": "resolve", "done": True}]
