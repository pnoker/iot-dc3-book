from __future__ import annotations

import pytest

from core.rag import RAGEngine
from core.rag_chunking import split_text
from core.rag_pdf import extract_pdf_pages


def test_rag_rejects_overlap_not_smaller_than_chunk_size(tmp_path) -> None:
    with pytest.raises(ValueError, match="chunk_overlap 必须小于 chunk_size"):
        RAGEngine(embed_fn=lambda text: [0.0], chunk_size=100, chunk_overlap=100, persist_dir=str(tmp_path))


def test_rag_status_reports_empty_index_as_unhealthy(tmp_path) -> None:
    engine = RAGEngine(embed_fn=lambda text: [0.0], persist_dir=str(tmp_path))

    status = engine.get_status()

    assert status["chunk_count"] == 0
    assert status["healthy"] is False
    assert status["persist_dir"] == str(tmp_path)


def test_split_text_uses_langchain_recursive_splitter(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeSplitter:
        def __init__(self, **kwargs: object) -> None:
            calls.append(kwargs)

        def split_text(self, text: str) -> list[str]:
            return [f"split:{text}"]

    monkeypatch.setattr("core.rag_chunking.RecursiveCharacterTextSplitter", FakeSplitter)

    chunks = split_text("物联网平台需要端边云协同。", chunk_size=100, chunk_overlap=20)

    assert chunks == ["split:物联网平台需要端边云协同。"]
    assert calls == [
        {
            "chunk_size": 100,
            "chunk_overlap": 20,
            "separators": ["\n\n", "\n", "。", "；", ".", " ", ""],
            "keep_separator": True,
        }
    ]


def test_extract_pdf_pages_uses_pymupdf4llm_markdown(monkeypatch) -> None:
    monkeypatch.setattr(
        "core.rag_pdf.pymupdf4llm.to_markdown",
        lambda pdf_path, page_chunks: [
            {"metadata": {"page": 1}, "text": "# 第一章 总览\n正文"},
            {"metadata": {"page": 2}, "text": "延续正文"},
        ],
    )

    pages = extract_pdf_pages("book.pdf")

    assert pages == [
        {"page": 1, "text": "# 第一章 总览\n正文", "section": "第一章 总览"},
        {"page": 2, "text": "延续正文", "section": "第一章 总览"},
    ]


def test_extract_pdf_pages_propagates_wrapped_keyboard_interrupt(monkeypatch) -> None:
    def interrupted_markdown(pdf_path: str, page_chunks: bool) -> object:
        raise RuntimeError("Director error: <class 'KeyboardInterrupt'>")

    monkeypatch.setattr("core.rag_pdf.pymupdf4llm.to_markdown", interrupted_markdown)

    with pytest.raises(KeyboardInterrupt):
        extract_pdf_pages("book.pdf")
