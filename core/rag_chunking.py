"""
RAG 文本分块工具
"""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

DEFAULT_SEPARATORS = ["\n\n", "\n", "。", "；", ".", " ", ""]


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """使用 LangChain 递归文本切分器按语义边界分块。"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=DEFAULT_SEPARATORS,
        keep_separator=True,
    )
    return [chunk.strip() for chunk in splitter.split_text(text) if chunk.strip()]
