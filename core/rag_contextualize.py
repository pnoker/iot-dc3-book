"""
Contextual Retrieval - 入库前给分块补全局上下文

参考 Anthropic Contextual Retrieval：孤立分块脱离原文语境后检索命中率低。
入库前用 LLM 为每个分块生成一句情境化前缀（说明它出自哪本书/哪节、在讲什么），
拼在分块正文前一起嵌入，让零碎片段重新锚定到全局语境。

成本敏感：对每个分块一次 LLM 调用。默认关闭，需在 references.yaml 显式开启。
启用后若 LLM 返回空内容或调用失败，直接报错，避免索引在半情境化状态下继续写入。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.log import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = get_logger("rag")

_CONTEXT_SYSTEM = """你为技术文档的检索分块生成简短情境说明。
给定文档来源、章节标题和一段正文，用一句话（不超过50字）说明这段内容属于什么主题、讲的是什么，
以便它被单独检索时仍能被正确理解。只输出这句情境说明，不要复述原文，不要加引号。"""


def contextualize_chunk(llm: Any, source: str, section: str, chunk_text: str) -> str:
    """为单个分块生成情境前缀并拼接。"""
    user_prompt = f"# 文档来源\n{source}\n# 章节\n{section}\n# 正文\n{chunk_text[:800]}\n\n请输出一句情境说明。"
    context = llm.chat(_CONTEXT_SYSTEM, user_prompt, temperature=0.0, max_tokens=120).strip()
    if not context:
        raise ValueError(f"分块情境化返回空内容: {source} / {section}")
    return f"[情境] {context}\n\n{chunk_text}"


def contextualize_batch(
        llm: Any, source: str, sections: Sequence[str], chunks: Sequence[str]
) -> list[str]:
    """批量情境化一个文件的分块。sections 与 chunks 一一对应。"""
    return [contextualize_chunk(llm, source, sec, ch) for sec, ch in zip(sections, chunks, strict=True)]
