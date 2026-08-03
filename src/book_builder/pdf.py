"""PDF 导出与封面渲染：Pandoc + Chrome headless。"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from html import escape
from pathlib import Path
from typing import Any

from jinja2 import Environment, select_autoescape

from book_builder.log import get_logger

logger = get_logger("pdf")

_DIVIDER_MARKER_RE = re.compile(r"BOOK_DIVIDER:([a-z]+-\d{2})")


def generate_pdf_output(
    markdown_file: str | Path,
    pdf_file: str | Path,
    *,
    css_file: str | Path | None = None,
    chrome_bin: str | None = None,
    pandoc_bin: str = "pandoc",
    cover_html: str | Path | None = None,
    metadata: dict[str, Any] | None = None,
    divider_images: dict[str, str | Path] | None = None,
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
    divider_html = pdf_path.with_name(".book_dividers.html")
    divider_pdf = pdf_path.with_name(".book_dividers.pdf")
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
    divider_ids = list(dict.fromkeys(_DIVIDER_MARKER_RE.findall(body_text)))
    divider_paths = _resolve_divider_paths(divider_ids, divider_images)
    if has_cover:
        body_text = re.sub(r"^\s*!\[[^\]]*\]\(cover\.png\)\s*\n", "", body_text, count=1)
    pandoc_input = pdf_path.with_name(".book_body.md")

    try:
        pandoc_input.write_text(body_text, encoding="utf-8")

        # pandoc: markdown → html
        cmd = [
            resolved_pandoc, str(pandoc_input), "-o", str(html_path),
            "--standalone", "--from", "markdown+pipe_tables+fenced_code_blocks+raw_html",
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

        if divider_ids:
            _render_divider_pdf(
                chrome,
                divider_ids,
                divider_paths,
                divider_html,
                divider_pdf,
            )

        rendered_cover: Path | None = None
        if has_cover:
            cover_cmd = [
                chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={cover_pdf}", cover_path.resolve().as_uri(),
            ]
            cover_done = subprocess.run(cover_cmd, check=False, capture_output=True, text=True)
            if cover_done.returncode == 0 and cover_pdf.exists():
                rendered_cover = cover_pdf
            else:
                logger.warning("封面 PDF 渲染失败，继续输出正文: %s", cover_done.stderr.strip())

        _merge_pdf_pages(
            pdf_path,
            body_pdf,
            divider_ids,
            divider_pdf if divider_ids else None,
            rendered_cover,
        )
        _add_pdf_outlines(pdf_path, markdown_file)
    finally:
        for tmp in (pandoc_input, html_path, body_pdf, cover_pdf, divider_html, divider_pdf):
            tmp.unlink(missing_ok=True)
        if cover_path and cover_path != cover_template:
            cover_path.unlink(missing_ok=True)

    logger.info("PDF 输出完成: %s", pdf_path)
    return str(pdf_path)


def _resolve_divider_paths(
    divider_ids: list[str],
    divider_images: dict[str, str | Path] | None,
) -> dict[str, Path]:
    if not divider_ids:
        return {}
    if divider_images is None:
        raise RuntimeError("Markdown 包含篇章扉页，但未提供扉页 PNG。")
    paths: dict[str, Path] = {}
    for divider_id in divider_ids:
        image = divider_images.get(divider_id)
        if image is None:
            raise RuntimeError(f"缺少篇章扉页 PNG: {divider_id}")
        path = Path(image)
        if not path.exists():
            raise FileNotFoundError(f"篇章扉页 PNG 不存在: {path}")
        paths[divider_id] = path
    return paths


def _render_divider_pdf(
    chrome: str,
    divider_ids: list[str],
    divider_paths: dict[str, Path],
    html_path: Path,
    pdf_path: Path,
) -> None:
    pages = "\n".join(
        '<section class="page"><img src="'
        f'{escape(divider_paths[divider_id].resolve().as_uri(), quote=True)}'
        '" alt=""></section>'
        for divider_id in divider_ids
    )
    html_path.write_text(
        """<!doctype html>
<html><head><meta charset="utf-8"><style>
@page { size: A4; margin: 0; }
html, body { margin: 0; padding: 0; }
.page { width: 210mm; height: 297mm; margin: 0; overflow: hidden; break-after: page; page-break-after: always; }
.page:last-child { break-after: auto; page-break-after: auto; }
img { display: block; width: 210mm; height: 297mm; margin: 0; object-fit: fill; }
</style></head><body>"""
        + pages
        + "</body></html>",
        encoding="utf-8",
    )
    command = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--allow-file-access-from-files",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0 or not pdf_path.exists():
        raise RuntimeError(f"篇章扉页 PDF 生成失败: {completed.stderr.strip()}")


def _merge_pdf_pages(
    output_path: Path,
    body_pdf: Path,
    divider_ids: list[str],
    divider_pdf: Path | None,
    cover_pdf: Path | None,
) -> None:
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    if cover_pdf is not None:
        for page in PdfReader(str(cover_pdf)).pages:
            writer.add_page(page)

    divider_pages: dict[str, Any] = {}
    if divider_ids:
        if divider_pdf is None:
            raise RuntimeError("缺少篇章扉页 PDF。")
        rendered_pages = PdfReader(str(divider_pdf)).pages
        if len(rendered_pages) != len(divider_ids):
            raise RuntimeError(
                f"篇章扉页页数异常: 预期 {len(divider_ids)}，实际 {len(rendered_pages)}"
            )
        divider_pages = dict(zip(divider_ids, rendered_pages, strict=True))

    replaced: set[str] = set()
    for page in PdfReader(str(body_pdf)).pages:
        text = page.extract_text() or ""
        matches = _DIVIDER_MARKER_RE.findall(text)
        if not matches:
            writer.add_page(page)
            continue
        if len(matches) != 1 or matches[0] not in divider_pages:
            raise RuntimeError(f"无法识别篇章扉页占位标记: {matches}")
        divider_id = matches[0]
        writer.add_page(divider_pages[divider_id])
        replaced.add(divider_id)

    missing = set(divider_ids) - replaced
    if missing:
        raise RuntimeError(f"篇章扉页占位页未找到: {sorted(missing)}")
    with open(output_path, "wb") as stream:
        writer.write(stream)


def _add_pdf_outlines(pdf_path: Path, markdown_file: str | Path | None = None) -> None:
    """从 Markdown 解析标题层级（跳过代码块），按内容分布估算页码，生成 PDF 书签大纲。"""
    from pypdf import PdfReader, PdfWriter

    md_path = Path(markdown_file) if markdown_file else None
    headings: list[tuple[int, str]] = []  # (level, title)
    if md_path and md_path.exists():
        h_re = re.compile(r"^(#{1,3})\s+(.+)$")
        in_fence = False
        for line in md_path.read_text(encoding="utf-8").split("\n"):
            stripped = line.lstrip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence or stripped.startswith("book-figure"):
                continue
            m = h_re.match(line)
            if m:
                headings.append((len(m.group(1)), m.group(2).strip()))

    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    if not headings or total_pages < 2:
        return

    # 找到目录页（最后出现"目录"文本的页面）作为正文起点
    toc_end_page = 0
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if "目录" in text and any(
            marker in text for marker in ("基础篇", "第1章", "物联网概述")
        ):
            toc_end_page = i

    # 仅取正文标题（排除扉页和目录区）
    front_h1_set = {"关于作者", "序", "导读", "目录"}
    body_headings = [
        (lv, t) for (lv, t) in headings
        if not any(t.startswith(h) for h in front_h1_set)
        and "·" not in t  # 排除目录中的篇名（如"基础篇 · ..."）
        and not t.startswith("-")
    ]
    front_headings = [
        (lv, t) for (lv, t) in headings
        if any(t.startswith(h) for h in front_h1_set)
    ]

    # 估算正文页面数及每页容纳字符数
    body_pages = max(total_pages - toc_end_page - 1, 1)
    body_text = md_path.read_text(encoding="utf-8")
    toc_pos = body_text.find("\n# 目录")
    if toc_pos < 0:
        toc_pos = body_text.find("\n# 目录".replace(" ", ""))
    body_section = body_text[toc_pos:] if toc_pos >= 0 else body_text[10000:]
    body_chars = len(body_section)
    chars_per_page = body_chars / body_pages if body_pages > 0 else 3000

    # 为正文标题估算页码
    char_offset = 0
    heading_pages: list[tuple[int, str, int]] = []
    heading_positions: list[tuple[int, str, int]] = []

    for lv, title in body_headings:
        pos = body_section.find(title, char_offset)
        if pos < 0:
            char_offset += 100
            continue
        page = toc_end_page + 1 + int(pos / chars_per_page)
        page = min(page, total_pages - 1)
        heading_pages.append((page, title, lv))
        heading_positions.append((pos, title, lv))
        char_offset = pos + len(title)

    # 前置标题放在前几页
    for i, (lv, title) in enumerate(front_headings):
        heading_pages.insert(i, (min(i + 1, toc_end_page), title, lv))

    # 附录追加到末尾
    appendix = next(((lv, t) for (lv, t) in headings if t.startswith("附录")), None)
    if appendix:
        heading_pages.append((total_pages - 1, appendix[1], appendix[0]))

    # 去重并排序
    seen: set[tuple[str, int]] = set()
    unique: list[tuple[int, str, int]] = []
    for p, t, lv in sorted(heading_pages, key=lambda x: x[0]):
        key = (t, lv)
        if key not in seen:
            seen.add(key)
            unique.append((p, t, lv))

    # 写入带层级书签的 PDF
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    stack: list[tuple[object, int]] = []
    for page_num, title, level in unique:
        while stack and stack[-1][1] >= level:
            stack.pop()
        parent = stack[-1][0] if stack else None
        item = writer.add_outline_item(title, page_num, parent=parent)
        stack.append((item, level))

    with open(pdf_path, "wb") as f:
        writer.write(f)

    logger.info("PDF 书签大纲已生成: %d 条", len(unique))


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
