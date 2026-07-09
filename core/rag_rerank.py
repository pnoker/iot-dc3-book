"""
LLM rerank - 对混合检索候选做精排

RRF 融合后取前若干候选，交由 LLM 按与查询的相关性重排并截断。
rerank 默认关闭；一旦在 references.yaml 显式开启，解析或调用失败必须暴露，避免增强项静默失效。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.log import get_logger

if TYPE_CHECKING:
    from core.state import ReferenceChunk

logger = get_logger("rag")

_RERANK_SYSTEM = """你是检索结果精排器。给定查询和若干候选段落，按每段与查询的相关性排序。
只做排序，不改写内容。输出严格 JSON：
{"ranking": [{"index": 候选编号, "score": 0到10的相关性分}]}
ranking 按相关性从高到低排列，只包含真正相关的候选。"""


def rerank_chunks(
        llm: Any, query: str, chunks: list[ReferenceChunk], top_k: int, preview_chars: int = 300
) -> list[ReferenceChunk]:
    """用 LLM 对候选精排，返回 top_k。"""
    if len(chunks) <= 1:
        return chunks[:top_k]

    listing = "\n\n".join(
        f"[{i}] 来源: {c.source_file} | {c.chapter_or_section}\n{c.text[:preview_chars]}"
        for i, c in enumerate(chunks)
    )
    user_prompt = f"# 查询\n{query}\n\n# 候选段落\n{listing}\n\n请输出严格 JSON 排序。"

    result = llm.chat_json(_RERANK_SYSTEM, user_prompt, temperature=0.0)
    order = _parse_ranking(result, len(chunks))
    if not order:
        raise ValueError("rerank 未返回有效排序")
    reranked = [_rescore(chunks[idx], rank, score) for rank, (idx, score) in enumerate(order)]
    logger.debug("rerank: %d 候选 → 取前 %d", len(chunks), top_k)
    return reranked[:top_k]


def _rescore(chunk: ReferenceChunk, rank: int, score: float | None) -> ReferenceChunk:
    """按精排结果回写 relevance_score，使精排顺序编码进分数，不被下游二次排序抵消。

    有 LLM 打分则归一化到 (0,1]（10 分制 → /10），无分则按名次递减；
    两者都叠加一个随名次单调下降的小项，保证严格降序、消除并列。
    """
    base = max(0.0, min(score / 10.0, 1.0)) if score is not None else 0.0
    return chunk.model_copy(update={"relevance_score": base + 1.0 / (rank + 2)})


def _parse_ranking(result: dict[str, Any], n: int) -> list[tuple[int, float | None]]:
    """从 LLM 响应解析出有效且去重的 (候选下标, 相关性分) 序列。分缺失或非法为 None。"""
    ranking = result.get("ranking")
    if not isinstance(ranking, list):
        return []
    order: list[tuple[int, float | None]] = []
    seen: set[int] = set()
    for item in ranking:
        if not isinstance(item, dict):
            continue
        idx = item.get("index")
        if isinstance(idx, int) and 0 <= idx < n and idx not in seen:
            seen.add(idx)
            raw = item.get("score")
            score = float(raw) if isinstance(raw, (int, float)) else None
            order.append((idx, score))
    return order
