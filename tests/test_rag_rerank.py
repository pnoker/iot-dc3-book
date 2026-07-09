from __future__ import annotations

import pytest

from core.rag_rerank import _parse_ranking, rerank_chunks
from core.state import ReferenceChunk


def _chunk(text: str) -> ReferenceChunk:
    return ReferenceChunk(source_file="s", chapter_or_section="c", text=text, relevance_score=0.0)


class FakeLLM:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls = 0

    def chat_json(self, system: str, user: str, temperature: float | None = None) -> dict:
        self.calls += 1
        return self.response


def test_rerank_reorders_and_truncates() -> None:
    chunks = [_chunk("A"), _chunk("B"), _chunk("C")]
    llm = FakeLLM({"ranking": [{"index": 2, "score": 9}, {"index": 0, "score": 5}, {"index": 1, "score": 3}]})

    result = rerank_chunks(llm, "q", chunks, top_k=2)

    assert [c.text for c in result] == ["C", "A"]  # 按 LLM 排序取前 2


def test_rerank_rewrites_score_to_encode_order() -> None:
    # 精排顺序必须写入 relevance_score，否则会被下游按分数二次排序抵消
    chunks = [_chunk("A"), _chunk("B"), _chunk("C")]
    llm = FakeLLM({"ranking": [{"index": 2, "score": 9}, {"index": 0, "score": 5}, {"index": 1, "score": 3}]})

    result = rerank_chunks(llm, "q", chunks, top_k=3)

    scores = [c.relevance_score for c in result]
    assert scores == sorted(scores, reverse=True)  # 分数严格随精排名次递减
    assert len(set(scores)) == len(scores)  # 无并列，下游 sort 不会打乱精排顺序


def test_rerank_rescore_without_llm_score_still_descends() -> None:
    # LLM 未给 score 时仍按名次回写严格递减的分数
    chunks = [_chunk("A"), _chunk("B")]
    llm = FakeLLM({"ranking": [{"index": 1}, {"index": 0}]})

    result = rerank_chunks(llm, "q", chunks, top_k=2)

    assert [c.text for c in result] == ["B", "A"]
    assert result[0].relevance_score > result[1].relevance_score


def test_rerank_rejects_bad_response() -> None:
    chunks = [_chunk("A"), _chunk("B")]
    llm = FakeLLM({"garbage": True})

    with pytest.raises(ValueError, match="rerank 未返回有效排序"):
        rerank_chunks(llm, "q", chunks, top_k=2)


def test_rerank_raises_when_llm_raises() -> None:
    chunks = [_chunk("A"), _chunk("B")]

    class BoomLLM:
        def chat_json(self, *a, **k):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        rerank_chunks(BoomLLM(), "q", chunks, top_k=1)


def test_rerank_single_candidate_skips_llm() -> None:
    llm = FakeLLM({"ranking": []})
    result = rerank_chunks(llm, "q", [_chunk("A")], top_k=5)

    assert [c.text for c in result] == ["A"]
    assert llm.calls == 0  # 单候选无需 rerank


def test_parse_ranking_dedups_and_bounds() -> None:
    order = _parse_ranking(
        {"ranking": [{"index": 1, "score": 8}, {"index": 1}, {"index": 9}, {"index": 0, "score": 4}]}, n=3
    )
    assert order == [(1, 8.0), (0, 4.0)]  # 去重 + 越界(9)剔除，保留相关性分

    # score 缺失或非法 → None，index 仍保留
    no_score = _parse_ranking({"ranking": [{"index": 0}, {"index": 1, "score": "x"}]}, n=2)
    assert no_score == [(0, None), (1, None)]
