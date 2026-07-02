"""
RAG 文本分块工具
"""

from __future__ import annotations


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """按 chunk_size 分块，尽量保留句子边界。"""
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            for sep in ["。", "\n", ".", "；"]:
                pos = text.rfind(sep, start + chunk_size // 2, end)
                if pos > start:
                    end = pos + 1
                    break
        chunks.append(text[start:end].strip())
        start = end - chunk_overlap
    return chunks
