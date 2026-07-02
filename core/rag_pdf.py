"""
PDF 文本提取工具
"""

from __future__ import annotations

from typing import TypedDict


class PdfPage(TypedDict):
    page: int
    text: str
    section: str


def extract_pdf_pages(pdf_path: str) -> list[PdfPage]:
    """提取 PDF 文本，按页提取并尝试识别章节。"""
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    pages: list[PdfPage] = []
    current_section = "前言"
    for index, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        for line in text.split("\n"):
            line = line.strip()
            if any(line.startswith(prefix) for prefix in ["第", "Chapter", "CHAPTER"]) and len(line) < 50:
                current_section = line
                break
        pages.append({"page": index + 1, "text": text, "section": current_section})
    return pages
