from __future__ import annotations

import pytest

from core.rag import RAGEngine
from core.rag_chunking import split_text
from core.rag_pdf import _page_has_ocr_candidate, extract_pdf_pages


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


def test_extract_pdf_pages_uses_text_extraction_without_ocr_first(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def text_markdown(pdf_path: str, **kwargs: object) -> list[dict[str, object]]:
        calls.append({"pdf_path": pdf_path, **kwargs})
        return [
            {"metadata": {"page": 1}, "text": "# 第一章 总览\n正文"},
            {"metadata": {"page": 2}, "text": "延续正文"},
        ]

    monkeypatch.setattr("core.rag_pdf.pymupdf4llm.to_markdown", text_markdown)

    pages = extract_pdf_pages("book.pdf")

    assert pages == [
        {"page": 1, "text": "# 第一章 总览\n正文", "section": "第一章 总览"},
        {"page": 2, "text": "延续正文", "section": "第一章 总览"},
    ]
    assert calls == [{"pdf_path": "book.pdf", "page_chunks": True, "use_ocr": False}]


def test_extract_pdf_pages_ocr_fallbacks_empty_text_pages_only(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def markdown(pdf_path: str, **kwargs: object) -> list[dict[str, object]]:
        calls.append({"pdf_path": pdf_path, **kwargs})
        if kwargs.get("use_ocr") is False:
            return [
                {"metadata": {"page": 1}, "text": "# 第一章 总览\n正文"},
                {"metadata": {"page": 2}, "text": ""},
            ]
        return [{"metadata": {"page": 2}, "text": "OCR 识别出的图片文字"}]

    monkeypatch.setattr("core.rag_pdf.pymupdf4llm.to_markdown", markdown)
    monkeypatch.setattr("core.rag_pdf._filter_ocr_candidate_page_indexes", lambda pdf_path, page_indexes: page_indexes)

    pages = extract_pdf_pages("book.pdf")

    assert pages == [
        {"page": 1, "text": "# 第一章 总览\n正文", "section": "第一章 总览"},
        {"page": 2, "text": "OCR 识别出的图片文字", "section": "第一章 总览"},
    ]
    assert calls == [
        {"pdf_path": "book.pdf", "page_chunks": True, "use_ocr": False},
        {
            "pdf_path": "book.pdf",
            "page_chunks": True,
            "pages": [1],
            "use_ocr": True,
            "force_ocr": True,
        },
    ]


def test_extract_pdf_pages_skips_ocr_for_pages_with_only_tiny_images(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def markdown(pdf_path: str, **kwargs: object) -> list[dict[str, object]]:
        calls.append({"pdf_path": pdf_path, **kwargs})
        return [
            {"metadata": {"page": 1}, "text": "# 第一章 总览\n正文"},
            {"metadata": {"page": 2}, "text": ""},
        ]

    monkeypatch.setattr("core.rag_pdf.pymupdf4llm.to_markdown", markdown)
    monkeypatch.setattr("core.rag_pdf._filter_ocr_candidate_page_indexes", lambda pdf_path, page_indexes: [])

    pages = extract_pdf_pages("book.pdf")

    assert pages == [{"page": 1, "text": "# 第一章 总览\n正文", "section": "第一章 总览"}]
    assert calls == [{"pdf_path": "book.pdf", "page_chunks": True, "use_ocr": False}]


def test_page_has_ocr_candidate_rejects_tiny_images(monkeypatch) -> None:
    monkeypatch.setattr("core.rag_pdf.pymupdf.open", lambda pdf_path: FakePdfDocument(tiny_image_blocks()))

    assert _page_has_ocr_candidate("book.pdf", 0) is False


def test_page_has_ocr_candidate_accepts_large_images(monkeypatch) -> None:
    monkeypatch.setattr("core.rag_pdf.pymupdf.open", lambda pdf_path: FakePdfDocument(large_image_blocks()))

    assert _page_has_ocr_candidate("book.pdf", 0) is True


def test_extract_pdf_pages_propagates_wrapped_keyboard_interrupt(monkeypatch) -> None:
    def interrupted_markdown(pdf_path: str, **kwargs: object) -> object:
        raise RuntimeError("Director error: <class 'KeyboardInterrupt'>")

    monkeypatch.setattr("core.rag_pdf.pymupdf4llm.to_markdown", interrupted_markdown)

    with pytest.raises(KeyboardInterrupt):
        extract_pdf_pages("book.pdf")


class FakeRect:
    width = 612
    height = 792


class FakePdfPage:
    rect = FakeRect()

    def __init__(self, blocks: list[dict[str, object]]) -> None:
        self._blocks = blocks

    def get_text(self, kind: str, **kwargs: object) -> dict[str, object]:
        assert kind == "dict"
        return {"blocks": self._blocks}


class FakePdfDocument:
    page_count = 1

    def __init__(self, blocks: list[dict[str, object]]) -> None:
        self._blocks = blocks

    def load_page(self, page_index: int) -> FakePdfPage:
        assert page_index == 0
        return FakePdfPage(self._blocks)

    def close(self) -> None:
        pass


def tiny_image_blocks() -> list[dict[str, object]]:
    return [{"type": 1, "bbox": (10, 10, 12, 46), "width": 2, "height": 36}]


def large_image_blocks() -> list[dict[str, object]]:
    return [{"type": 1, "bbox": (40, 60, 520, 700), "width": 1600, "height": 2200}]
