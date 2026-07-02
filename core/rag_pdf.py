"""
PDF 文本提取工具
"""

from __future__ import annotations

from typing import TypedDict

import pymupdf4llm


class PdfPage(TypedDict):
    page: int
    text: str
    section: str


def extract_pdf_pages(pdf_path: str) -> list[PdfPage]:
    """使用 pymupdf4llm 提取 Markdown 文本并保留页码。"""
    chunks = pymupdf4llm.to_markdown(pdf_path, page_chunks=True)
    pages: list[PdfPage] = []
    current_section = "前言"
    for index, chunk in enumerate(chunks):
        text = str(chunk.get("text") or "")
        if not text.strip():
            continue
        section = _detect_section(text)
        if section:
            current_section = section
        metadata = chunk.get("metadata") if isinstance(chunk, dict) else {}
        page_number = _extract_page_number(metadata, index)
        pages.append({"page": page_number, "text": text, "section": current_section})
    return pages


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
