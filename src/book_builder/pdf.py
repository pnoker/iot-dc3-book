"""PDF 导出与封面渲染：Pandoc + Chrome headless。"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from jinja2 import Environment, select_autoescape

from book_builder.log import get_logger

logger = get_logger("pdf")


def generate_pdf_output(
    markdown_file: str | Path,
    pdf_file: str | Path,
    *,
    css_file: str | Path | None = None,
    chrome_bin: str | None = None,
    pandoc_bin: str = "pandoc",
    cover_html: str | Path | None = None,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    """从 book.md 生成 PDF：pandoc 转 HTML → Chrome headless 转 PDF，封面单独渲染合并。

    中间文件（.book_body.md、book.html、临时 PDF）在导出后自动清理，
    最终只保留 book.pdf。
    """
    markdown_path = Path(markdown_file)
    if not markdown_path.exists():
        raise FileNotFoundError(f"Markdown 文件不存在: {markdown_path}")
    resolved_pandoc = shutil.which(pandoc_bin)
    if resolved_pandoc is None:
        raise RuntimeError("未找到 pandoc，无法生成 PDF。")
    chrome = chrome_bin or _find_chrome()
    if chrome is None:
        logger.warning("未找到 Chrome/Edge，跳过 PDF 生成。安装后可自动生成。")
        return None

    pdf_path = Path(pdf_file)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    html_path = pdf_path.with_suffix(".html")
    body_pdf = pdf_path.with_name(".book_body.pdf")
    cover_pdf = pdf_path.with_name(".book_cover.pdf")
    cover_template = Path(cover_html) if cover_html else None
    cover_path = (
        _render_cover_html(cover_template, metadata)
        if cover_template and cover_template.exists()
        else None
    )
    has_cover = bool(cover_path and cover_path.exists())

    # pandoc 输入：去图片属性 + 去封面 cover.png 引用（封面单独渲染）
    text = markdown_path.read_text(encoding="utf-8")
    body_text = re.sub(r"(!\[[^\]]*\]\([^)]*\))\s*\{[^}]*\}", r"\1", text)
    if has_cover:
        body_text = re.sub(r"^\s*!\[[^\]]*\]\(cover\.png\)\s*\n", "", body_text, count=1)
    pandoc_input = pdf_path.with_name(".book_body.md")

    try:
        pandoc_input.write_text(body_text, encoding="utf-8")

        # pandoc: markdown → html
        cmd = [
            resolved_pandoc, str(pandoc_input), "-o", str(html_path),
            "--standalone", "--from", "markdown+pipe_tables+fenced_code_blocks",
        ]
        for key, value in _pandoc_metadata(metadata).items():
            cmd += ["--metadata", f"{key}={value}"]
        if css_file and Path(css_file).exists():
            css_href = os.path.relpath(Path(css_file).resolve(), html_path.parent.resolve())
            cmd += ["--css", css_href]
        completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(f"pandoc 生成 HTML 失败: {completed.stderr.strip()}")

        # Chrome headless: html → pdf
        chrome_cmd = [
            chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
            f"--print-to-pdf={body_pdf}", html_path.resolve().as_uri(),
        ]
        completed = subprocess.run(chrome_cmd, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(f"Chrome 生成 PDF 失败: {completed.stderr.strip()}")

        # 合并封面
        if has_cover:
            cover_cmd = [
                chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={cover_pdf}", cover_path.resolve().as_uri(),
            ]
            cover_done = subprocess.run(cover_cmd, check=False, capture_output=True, text=True)
            if cover_done.returncode == 0 and cover_pdf.exists() and body_pdf.exists():
                try:
                    from pypdf import PdfReader, PdfWriter
                    writer = PdfWriter()
                    for page in PdfReader(str(cover_pdf)).pages:
                        writer.add_page(page)
                    for page in PdfReader(str(body_pdf)).pages:
                        writer.add_page(page)
                    with open(pdf_path, "wb") as f:
                        writer.write(f)
                except Exception as exc:
                    logger.warning("封面 PDF 合并失败，输出仅正文 PDF: %s", exc)
                    body_pdf.replace(pdf_path)
            else:
                logger.warning("封面 PDF 渲染失败，输出仅正文 PDF: %s", cover_done.stderr.strip())
                body_pdf.replace(pdf_path)
        else:
            body_pdf.replace(pdf_path)
    finally:
        # 清理所有中间文件，只保留 book.pdf
        for tmp in (pandoc_input, html_path, body_pdf, cover_pdf):
            tmp.unlink(missing_ok=True)
        if cover_path and cover_path != cover_template:
            cover_path.unlink(missing_ok=True)

    logger.info("PDF 输出完成: %s", pdf_path)
    return str(pdf_path)


def generate_cover_image(
    cover_html: str | Path,
    output_png: str | Path,
    *,
    chrome_bin: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """用 Chrome headless 把封面 HTML 模板转为 PNG。"""
    chrome = chrome_bin or _find_chrome()
    if chrome is None:
        logger.warning("未找到 Chrome，跳过封面图生成。")
        return
    cover_template = Path(cover_html)
    if not cover_template.exists():
        return
    cover_path = _render_cover_html(cover_template, metadata)
    png_path = Path(output_png)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.unlink(missing_ok=True)

    # HTML → 一页 A4 PDF
    cover_pdf = png_path.with_name(".cover_tmp.pdf")
    pdf_cmd = [
        chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
        f"--print-to-pdf={cover_pdf}", cover_path.resolve().as_uri(),
    ]
    pdf_done = subprocess.run(pdf_cmd, check=False, capture_output=True, text=True)

    # PDF → PNG
    if pdf_done.returncode == 0 and cover_pdf.exists():
        pdftoppm = shutil.which("pdftoppm")
        if pdftoppm:
            output_prefix = png_path.with_suffix("")
            conv = subprocess.run(
                [pdftoppm, "-png", "-r", "300", "-singlefile", str(cover_pdf), str(output_prefix)],
                check=False, capture_output=True, text=True,
            )
            if conv.returncode == 0 and png_path.exists():
                cover_pdf.unlink(missing_ok=True)
                cover_path.unlink(missing_ok=True)
                logger.info("封面图生成: %s", png_path)
                return
        sips = shutil.which("sips")
        if sips:
            conv = subprocess.run(
                [sips, "-s", "format", "png", "-z", "3508", "2480", str(cover_pdf), "--out", str(png_path)],
                check=False, capture_output=True, text=True,
            )
            cover_pdf.unlink(missing_ok=True)
            if conv.returncode == 0 and png_path.exists():
                cover_path.unlink(missing_ok=True)
                logger.info("封面图生成: %s", png_path)
                return
        cover_pdf.unlink(missing_ok=True)

    # 回退：直接截图
    fallback = [
        chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
        "--default-background-color=00000000", f"--screenshot={png_path}",
        "--window-size=1240,1754", "--force-device-scale-factor=1",
        cover_path.resolve().as_uri(),
    ]
    completed = subprocess.run(fallback, check=False, capture_output=True, text=True)
    cover_path.unlink(missing_ok=True)
    if completed.returncode == 0 and png_path.exists():
        logger.info("封面图生成（截图回退）: %s", png_path)
    else:
        logger.warning("封面图生成失败: %s", completed.stderr.strip())


def _render_cover_html(
    cover_template: Path,
    metadata: dict[str, Any] | None,
) -> Path:
    """用书籍元数据渲染临时封面，同时保留模板目录中的相对资源路径。"""
    template = Environment(
        autoescape=select_autoescape(enabled_extensions=("html",)),
    ).from_string(cover_template.read_text(encoding="utf-8"))
    rendered = template.render(**(metadata or {}))
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".html",
        prefix=".cover-rendered-",
        dir=cover_template.parent,
        delete=False,
    ) as temporary:
        temporary.write(rendered)
        return Path(temporary.name)


def _pandoc_metadata(metadata: dict[str, Any] | None) -> dict[str, str]:
    """筛选并映射 Pandoc 使用的书籍元数据。"""
    if not metadata:
        return {}
    field_names = {
        "title": "title",
        "subtitle": "subtitle",
        "author": "author",
        "language": "lang",
        "isbn": "isbn",
        "publisher": "publisher",
        "edition": "edition",
    }
    return {
        pandoc_name: str(metadata[source_name])
        for source_name, pandoc_name in field_names.items()
        if metadata.get(source_name) not in (None, "")
    }


def _find_chrome() -> str | None:
    """查找本机 Chromium 内核浏览器可执行文件。"""
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return shutil.which("chromium") or shutil.which("google-chrome")
