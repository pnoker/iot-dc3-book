"""
PDF 文本提取工具
"""

from __future__ import annotations

from typing import Any, TypedDict, cast

import pymupdf
import pymupdf4llm

MIN_OCR_IMAGE_WIDTH = 24
MIN_OCR_IMAGE_HEIGHT = 24
MIN_OCR_IMAGE_AREA_RATIO = 0.01


class PdfPage(TypedDict):
    page: int
    text: str
    section: str


def extract_pdf_pages(pdf_path: str) -> list[PdfPage]:
    """优先提取 PDF 内嵌文本，仅对空文本页使用 OCR。"""
    chunks = _to_markdown(pdf_path, page_chunks=True, use_ocr=False)
    empty_page_indexes = _find_empty_page_indexes(chunks)
    ocr_text_by_page = _extract_ocr_text_by_page(pdf_path, empty_page_indexes)

    pages: list[PdfPage] = []
    current_section = "前言"
    for index, chunk in enumerate(chunks):
        text = str(chunk.get("text") or "")
        metadata = chunk.get("metadata") if isinstance(chunk, dict) else {}
        page_number = _extract_page_number(metadata, index)
        if not text.strip():
            text = ocr_text_by_page.get(page_number, "")
            if not text.strip():
                continue
        section = _detect_section(text)
        if section:
            current_section = section
        pages.append({"page": page_number, "text": text, "section": current_section})
    return pages


def _to_markdown(pdf_path: str, **kwargs: object) -> list[dict[str, object]]:
    try:
        return cast("list[dict[str, object]]", pymupdf4llm.to_markdown(pdf_path, **kwargs))
    except Exception as exc:
        if "KeyboardInterrupt" in str(exc):
            raise KeyboardInterrupt from exc
        raise


def _find_empty_page_indexes(chunks: list[dict[str, object]]) -> list[int]:
    return [index for index, chunk in enumerate(chunks) if not str(chunk.get("text") or "").strip()]


def _extract_ocr_text_by_page(pdf_path: str, page_indexes: list[int]) -> dict[int, str]:
    if not page_indexes:
        return {}
    page_indexes = _filter_ocr_candidate_page_indexes(pdf_path, page_indexes)
    if not page_indexes:
        return {}
    ocr_chunks = _to_markdown(pdf_path, page_chunks=True, pages=page_indexes, use_ocr=True, force_ocr=True)
    ocr_text_by_page: dict[int, str] = {}
    for index, chunk in enumerate(ocr_chunks):
        text = str(chunk.get("text") or "")
        if not text.strip():
            continue
        metadata = chunk.get("metadata") if isinstance(chunk, dict) else {}
        page_number = _extract_page_number(metadata, page_indexes[index] if index < len(page_indexes) else index)
        ocr_text_by_page[page_number] = text
    return ocr_text_by_page


def _filter_ocr_candidate_page_indexes(pdf_path: str, page_indexes: list[int]) -> list[int]:
    doc = cast("Any", pymupdf.open)(pdf_path)
    try:
        return [page_index for page_index in page_indexes if _document_page_has_ocr_candidate(doc, page_index)]
    finally:
        doc.close()


def _page_has_ocr_candidate(pdf_path: str, page_index: int) -> bool:
    doc = cast("Any", pymupdf.open)(pdf_path)
    try:
        return _document_page_has_ocr_candidate(doc, page_index)
    finally:
        doc.close()


def _document_page_has_ocr_candidate(doc: Any, page_index: int) -> bool:
    if page_index >= doc.page_count:
        return False
    page = doc.load_page(page_index)
    page_area = float(page.rect.width * page.rect.height)
    blocks = page.get_text("dict", flags=pymupdf.TEXT_PRESERVE_IMAGES).get("blocks", [])
    return any(_block_is_ocr_candidate(block, page_area) for block in blocks if isinstance(block, dict))


def _block_is_ocr_candidate(block: dict[str, object], page_area: float) -> bool:
    if block.get("type") != 1:
        return False
    bbox = block.get("bbox")
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return False
    width = _positive_float(block.get("width")) or _positive_float(bbox[2] - bbox[0])
    height = _positive_float(block.get("height")) or _positive_float(bbox[3] - bbox[1])
    if width < MIN_OCR_IMAGE_WIDTH or height < MIN_OCR_IMAGE_HEIGHT:
        return False
    visible_area = max(float(bbox[2] - bbox[0]), 0.0) * max(float(bbox[3] - bbox[1]), 0.0)
    return page_area <= 0 or visible_area / page_area >= MIN_OCR_IMAGE_AREA_RATIO


def _positive_float(value: object) -> float:
    if isinstance(value, int | float):
        return max(float(value), 0.0)
    return 0.0


def _detect_section(text: str) -> str:
    for line in text.split("\n"):
        section = line.strip().lstrip("#").strip()
        if any(section.startswith(prefix) for prefix in ["第", "Chapter", "CHAPTER"]) and len(section) < 50:
            return section
    return ""


def _extract_page_number(metadata: object, index: int) -> int:
    if isinstance(metadata, dict):
        page = metadata.get("page") or metadata.get("page_number")
        if isinstance(page, int):
            return page
        if isinstance(page, str) and page.isdigit():
            return int(page)
    return index + 1
