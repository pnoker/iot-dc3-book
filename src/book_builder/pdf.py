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

# 资料溯源标注（写作过程的来源标记，正式出版 PDF 不展示）
# 与 scripts/build_web.py 的 clean_citations 保持一致，保证 web 与 PDF 输出一致。
_CITE_BLOCK_RE = re.compile(r"（资料[^（）]*）")
_CITE_MARK_RE = re.compile(r"\[(?:S[^]]*|参考\d+|W-C7-[^]]*)\]")


def _clean_citations(md: str) -> str:
    """清除写作期资料溯源标注（整块 + 散落标记）；保留「参考5.2.2节」等章节引用与代码占位符。"""
    md = _CITE_BLOCK_RE.sub("", md)
    md = _CITE_MARK_RE.sub("", md)
    return md


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

    # pandoc 输入：去图片属性 + 去封面引用 + 清写作期溯源标注
    text = markdown_path.read_text(encoding="utf-8")
    text = _clean_citations(text)
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

        # Chrome headless: html → pdf（单次渲染，保证全书页码连续，无页眉页脚）
        chrome_cmd = [
            chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
            f"--print-to-pdf={body_pdf}", html_path.resolve().as_uri(),
        ]
        completed = subprocess.run(chrome_cmd, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(f"Chrome 生成 PDF 失败: {completed.stderr.strip()}")

        # 从 HTML 解析标题位置（用于书签 + 页眉章节映射）
        html_headings = _parse_html_headings(html_path, body_pdf)

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

        special_pages = _merge_pdf_pages(
            pdf_path,
            body_pdf,
            divider_ids,
            divider_pdf if divider_ids else None,
            rendered_cover,
        )
        _add_outlines_and_page_numbers(
            pdf_path,
            html_headings,
            cover_offset=1 if rendered_cover else 0,
            special_pages=special_pages,
        )
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
) -> set[int]:
    """合并封面 + 正文 + 扉页，返回合并后 PDF 中扉页/封面页的索引集合（这些页不加页眉页脚）。"""
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    special_pages: set[int] = set()  # 封面 + 扉页页索引
    out_idx = 0

    if cover_pdf is not None:
        for page in PdfReader(str(cover_pdf)).pages:
            writer.add_page(page)
            special_pages.add(out_idx)
            out_idx += 1

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
            out_idx += 1
            continue
        if len(matches) != 1 or matches[0] not in divider_pages:
            raise RuntimeError(f"无法识别篇章扉页占位标记: {matches}")
        divider_id = matches[0]
        writer.add_page(divider_pages[divider_id])
        special_pages.add(out_idx)
        out_idx += 1
        replaced.add(divider_id)

    missing = set(divider_ids) - replaced
    if missing:
        raise RuntimeError(f"篇章扉页占位页未找到: {sorted(missing)}")
    with open(output_path, "wb") as stream:
        writer.write(stream)
    return special_pages


def _parse_html_headings(html_path: Path, body_pdf: Path) -> list[tuple[int, str, int]]:
    """从 pandoc HTML 提取所有 <h1>/<h2>/<h3> 并按字符比例估算页码。

    返回: [(level, title, page_number), ...] 保持 HTML 中的出现顺序。
    """
    import html as html_mod
    from pypdf import PdfReader

    html_text = html_path.read_text(encoding="utf-8")
    for tag in ("head", "style", "script", "nav"):
        html_text = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", "", html_text, flags=re.DOTALL)

    body_m = re.search(r"<body[^>]*>(.*?)</body>", html_text, re.DOTALL)
    body_html = body_m.group(1) if body_m else html_text

    # 提取所有标题元素（pandoc 会对长标题折行，需空白归一）
    heading_re = re.compile(r"<(h[123])[^>]*>(.+?)</\1>", re.DOTALL)
    html_headings: list[tuple[int, int, str]] = []
    for m in heading_re.finditer(body_html):
        level = int(m.group(1)[1])
        raw = html_mod.unescape(re.sub(r"<[^>]+>", "", m.group(2)))
        text = re.sub(r"\s+", " ", raw).strip()
        if text:
            html_headings.append((m.start(), level, text))

    if not html_headings:
        return []

    # 正文纯文本（用于密度估算）
    body_text = re.sub(r"<[^>]+>", "", body_html)
    body_text = html_mod.unescape(body_text)
    body_text = re.sub(r"\s+", "", body_text)
    total_chars = len(body_text)
    if total_chars < 100:
        return []

    body_pages = max(len(PdfReader(str(body_pdf)).pages), 2) if body_pdf.exists() else 200

    result: list[tuple[int, str, int]] = []
    for pos, lv, title in html_headings:
        text_before = body_html[:pos]
        text_before_clean = re.sub(r"<[^>]+>", "", text_before)
        text_before_clean = html_mod.unescape(text_before_clean)
        text_before_clean = re.sub(r"\s+", "", text_before_clean)
        page = int(len(text_before_clean) / total_chars * body_pages)
        page = max(0, min(page, body_pages - 1))
        result.append((lv, title, page))

    logger.info("HTML 标题解析: %d 条, %d body pages", len(result), body_pages)
    return result


def _add_outlines_and_page_numbers(
    pdf_path: Path,
    html_headings: list[tuple[int, str, int]],
    cover_offset: int = 0,
    special_pages: set[int] | None = None,
) -> None:
    """用 reportlab 叠加层绘制页眉（章节名）+ 页脚（连续页码）+ 分格线，并写入三层书签。

    封面和篇章扉页（special_pages）不加页眉页脚，但仍占页码序列。
    """
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    if total < 2:
        return
    special = special_pages or set()

    # 过滤书名和分部标题，构建 (最终页码, 标题, 层级)
    heading_pages: list[tuple[int, str, int]] = []
    for lv, title, body_page in html_headings:
        if title == "从工业软件到 AI 智能体":
            continue
        if "·" in title and any(
            title.startswith(p) for p in ("基础篇", "技术篇", "应用篇")
        ):
            continue
        heading_pages.append((body_page + cover_offset, title, lv))
    if not heading_pages:
        return
    heading_pages.sort(key=lambda x: x[0])

    # 每页对应的章节名（从上一条 H1 继承）
    page_chapter = _build_page_chapter_map(heading_pages, total)

    # 生成 reportlab 叠加层并合并
    overlay_pdf = pdf_path.with_name(".header_footer.pdf")
    try:
        _draw_header_footer_overlay(
            overlay_pdf, total, page_chapter, cover_offset, special,
            page_size=(float(reader.pages[0].mediabox.width),
                       float(reader.pages[0].mediabox.height)),
        )
        overlay_reader = PdfReader(str(overlay_pdf))
        writer = PdfWriter()
        for i, page in enumerate(reader.pages):
            if i < len(overlay_reader.pages):
                page.merge_page(overlay_reader.pages[i])
            writer.add_page(page)

        # 三层书签
        seen: set[tuple[str, int]] = set()
        unique: list[tuple[int, str, int]] = []
        for p, t, lv in heading_pages:
            key = (t, lv)
            if key not in seen:
                seen.add(key)
                unique.append((p, t, lv))

        stack: list[tuple[object, int]] = []
        for page_num, title, level in unique:
            page_num = min(page_num, total - 1)
            if title == "目录":
                while stack:
                    stack.pop()
            while stack and stack[-1][1] >= level:
                stack.pop()
            parent = stack[-1][0] if stack else None
            item = writer.add_outline_item(title, page_num, parent=parent)
            if title != "目录":
                stack.append((item, level))

        with open(pdf_path, "wb") as f:
            writer.write(f)
    finally:
        overlay_pdf.unlink(missing_ok=True)

    logger.info("PDF 书签 + 页眉页脚: %d 条, %d 页", len(unique), total)


def _build_page_chapter_map(
    heading_pages: list[tuple[int, str, int]],
    total: int,
) -> dict[int, str]:
    """为每页分配页眉章节名（H1 → 章名，前置页 → 空，附录 → 附录）。"""
    front = {"关于作者", "序", "导读", "目录"}
    page_h1: dict[int, str] = {}
    for page_num, title, level in heading_pages:
        if level != 1:
            continue
        if title in front:
            page_h1[page_num] = ""  # 前置页不显示章节名页眉
        else:
            page_h1[page_num] = title
    # 向后填充
    page_chapter: dict[int, str] = {}
    current = ""
    for i in range(total):
        if i in page_h1:
            current = page_h1[i]
        page_chapter[i] = current
    return page_chapter


def _draw_header_footer_overlay(
    overlay_path: Path,
    total: int,
    page_chapter: dict[int, str],
    cover_offset: int,
    special_pages: set[int],
    page_size: tuple[float, float],
) -> None:
    """用 reportlab 生成透明叠加层：页眉章节名 + 页脚页码 + 上下分格线。

    封面和篇章扉页（special_pages）留白（有自己的设计），但页码序列连续。
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfgen import canvas

    cn_font = "STSong-Light"
    pdfmetrics.registerFont(UnicodeCIDFont(cn_font))

    w, h = page_size
    margin_x = 56.7  # 2cm
    gray = (0.55, 0.55, 0.55)
    line_gray = (0.8, 0.8, 0.8)

    c = canvas.Canvas(str(overlay_path), pagesize=(w, h))
    for i in range(total):
        # 封面和扉页留白（页码序列仍连续递增）
        if i >= cover_offset and i not in special_pages:
            page_no = i - cover_offset + 1  # 正文页码从 1 开始
            chapter = page_chapter.get(i, "")

            # ── 页眉 ──
            header_y = h - 48
            if chapter:
                c.setFont(cn_font, 8)
                c.setFillColorRGB(*gray)
                c.drawCentredString(w / 2, header_y, chapter)
                # 页眉分格线（仅当有章节名时绘制）
                c.setStrokeColorRGB(*line_gray)
                c.setLineWidth(0.5)
                c.line(margin_x, header_y - 6, w - margin_x, header_y - 6)

            # ── 页脚 ──
            footer_y = 40
            c.setStrokeColorRGB(*line_gray)
            c.setLineWidth(0.5)
            c.line(margin_x, footer_y + 10, w - margin_x, footer_y + 10)
            c.setFont("Helvetica", 8)
            c.setFillColorRGB(*gray)
            c.drawCentredString(w / 2, footer_y, f"— {page_no} —")

        c.showPage()
    c.save()


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
        chrome, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
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
        chrome, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
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
    """查找本机 Chromium 内核浏览器可执行文件（macOS / Linux / WSL 挂载的 Windows）。"""
    env_chrome = os.environ.get("DC3_CHROME") or os.environ.get("CHROME_PATH")
    if env_chrome and (Path(env_chrome).exists() or shutil.which(env_chrome)):
        return env_chrome
    candidates = [
        # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        # Windows（WSL 挂载点）
        "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
        "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        "/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return (
        shutil.which("chromium")
        or shutil.which("google-chrome")
        or shutil.which("microsoft-edge")
        or shutil.which("msedge")
    )
