"""输出模块：从手稿组装出版稿 Markdown，并通过 Pandoc + Chrome 生成 PDF。"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from book_builder.config import AppConfig, PartConfig
from book_builder.figures import FigureAsset, replace_book_figures_with_images
from book_builder.log import get_logger

logger = get_logger("output")


@lru_cache(maxsize=1)
def get_template_environment() -> Environment:
    template_dir = Path(__file__).resolve().parent / "templates"
    return Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


# ---------------------------------------------------------------------------
# Markdown 组装
# ---------------------------------------------------------------------------

def generate_markdown_output(
    chapters: dict[int, str],
    parts: list[PartConfig],
    cfg: AppConfig,
    output_dir: str | Path,
    *,
    figure_assets: list[FigureAsset] | None = None,
) -> dict[str, object]:
    """将全书内容输出为层级化 Markdown 与单文件 book.md。

    输出结构：
    output/
    ├── 00-封面.md
    ├── 01-作者简介.md
    ├── 02-序.md
    ├── 03-导读.md
    ├── 04-目录.md
    ├── 05-{part1.name}/
    │   ├── 01-{ch1.title}.md
    │   └── ...
    ├── 06-{part2.name}/
    ├── 07-{part3.name}/
    ├── 08-附录.md
    ├── book.md
    └── book_clean.md
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 封面图
    cover_html = out.parent / "book" / "cover.html"
    if cover_html.exists():
        _generate_cover_image(cover_html, out / "cover.png")

    env = get_template_environment()
    illustration_cfg = cfg.style.illustrations.model_dump()
    figure_marker = str(illustration_cfg.get("marker") or "book-figure")
    assets = figure_assets or []

    manuscript_parts: list[str] = []
    generated_files: list[str] = []

    # 封面
    cover = _render(env, "cover.md.j2")
    _write_file(out / "00-封面.md", cover, generated_files)
    manuscript_parts.append(cover)

    # 作者简介
    author_cfg = cfg.author
    profile = author_cfg.get("profile")
    if profile:
        author_md = _render(env, "author_profile.md.j2", profile=profile)
        _write_file(out / "01-作者简介.md", author_md, generated_files)
        manuscript_parts.append(author_md)

    # 序言 & 导读
    preface = author_cfg.get("preface")
    if preface:
        preface_md = _render(env, "preface.md.j2", preface=preface)
        reading_guide = _render(env, "reading_guide.md.j2", preface=preface, parts=parts)
        _write_file(out / "02-序.md", preface_md, generated_files)
        _write_file(out / "03-导读.md", reading_guide, generated_files)
        manuscript_parts.extend([preface_md, reading_guide])

    # 目录
    toc_content = _render(env, "toc.md.j2", parts=parts)
    _write_file(out / "04-目录.md", toc_content, generated_files)
    manuscript_parts.append(toc_content)

    # 篇章章节
    part_start_index = 5  # 前 4 个序号已用（封面/作者/序+导读/目录）
    for part_idx, part in enumerate(parts):
        dir_name = f"{part_idx + part_start_index:02d}-{part.name}"
        part_dir = out / dir_name
        part_dir.mkdir(parents=True, exist_ok=True)
        manuscript_parts.append(f"# {part.prefix}、{part.name}\n")

        for chapter in part.chapters:
            content = chapters.get(chapter.id)
            if content is None:
                logger.warning("第%d章(%s) 缺少手稿内容，已跳过", chapter.id, chapter.title)
                continue

            filename = f"{chapter.id:02d}-{chapter.title}.md"

            # 层级文件中用相对路径引用图片
            chapter_markdown = replace_book_figures_with_images(
                content, chapter.id, assets, marker=figure_marker, image_prefix="../",
            )
            # book.md 合集中用直接路径
            book_chapter_markdown = replace_book_figures_with_images(
                content, chapter.id, assets, marker=figure_marker,
            )

            _write_file(part_dir / filename, chapter_markdown, generated_files)
            manuscript_parts.append(book_chapter_markdown)

    # 附录
    appendix = _render(env, "appendix.md.j2")
    _write_file(out / "08-附录.md", appendix, generated_files)
    manuscript_parts.append(appendix)

    # 合成 book.md
    book_markdown_name = cfg.output.book_markdown
    book_path = out / book_markdown_name
    book_content = _join_markdown_parts(manuscript_parts)
    _write_file(book_path, book_content, generated_files)

    # 去 pandoc 图片属性的 clean 版
    clean_content = re.sub(r"(!\[[^\]]*\]\([^)]*\))\s*\{[^}]*\}", r"\1", book_content)
    _write_file(out / "book_clean.md", clean_content, generated_files)

    logger.info("Markdown 输出完成: %s (%d 个文件)", out, len(generated_files))
    return {
        "output_dir": str(out),
        "book_markdown": str(book_path),
        "book_clean": str(out / "book_clean.md"),
        "files": generated_files,
    }


# ---------------------------------------------------------------------------
# PDF 生成 (Pandoc + Chrome headless)
# ---------------------------------------------------------------------------

def generate_pdf_output(
    markdown_file: str | Path,
    pdf_file: str | Path,
    *,
    css_file: str | Path | None = None,
    chrome_bin: str | None = None,
    pandoc_bin: str = "pandoc",
    cover_html: str | Path | None = None,
) -> str | None:
    """从 Markdown 生成 PDF：pandoc 转 HTML → Chrome headless 转 PDF。"""
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

    cover_path = Path(cover_html) if cover_html else None
    has_cover = bool(cover_path and cover_path.exists())

    pandoc_input = markdown_path
    if has_cover:
        text = markdown_path.read_text(encoding="utf-8")
        stripped = re.sub(r"^\s*!\[[^\]]*\]\(cover\.png\)\s*\n", "", text, count=1)
        if stripped != text:
            pandoc_input = pdf_path.with_name(".book_body.md")
            pandoc_input.write_text(stripped, encoding="utf-8")

    # pandoc: markdown → html
    cmd = [
        resolved_pandoc, str(pandoc_input), "-o", str(html_path),
        "--standalone", "--from", "markdown+pipe_tables+fenced_code_blocks",
    ]
    if css_file and Path(css_file).exists():
        css_href = os.path.relpath(Path(css_file).resolve(), html_path.parent.resolve())
        cmd += ["--css", css_href]
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True, cwd=None)
    if completed.returncode != 0:
        raise RuntimeError(f"pandoc 生成 HTML 失败: {completed.stderr.strip()}")

    body_pdf = pdf_path.with_name(".book_body.pdf") if has_cover else pdf_path

    # Chrome headless: html → pdf
    chrome_cmd = [
        chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
        f"--print-to-pdf={body_pdf}", f"file://{html_path}",
    ]
    completed = subprocess.run(chrome_cmd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"Chrome 生成 PDF 失败: {completed.stderr.strip()}")

    # 合并封面
    if has_cover:
        cover_pdf = pdf_path.with_name(".book_cover.pdf")
        cover_cmd = [
            chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
            f"--print-to-pdf={cover_pdf}", f"file://{cover_path}",
        ]
        cover_done = subprocess.run(cover_cmd, check=False, capture_output=True, text=True)
        if cover_done.returncode == 0 and cover_pdf.exists():
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
                if body_pdf != pdf_path:
                    body_pdf.replace(pdf_path)
            finally:
                cover_pdf.unlink(missing_ok=True)
                if body_pdf != pdf_path:
                    body_pdf.unlink(missing_ok=True)
        else:
            logger.warning("封面 PDF 渲染失败，输出仅正文 PDF: %s", cover_done.stderr.strip())
            if body_pdf != pdf_path:
                body_pdf.replace(pdf_path)

    if pandoc_input != markdown_path:
        pandoc_input.unlink(missing_ok=True)

    logger.info("PDF 输出完成: %s", pdf_path)
    return str(pdf_path)


def _generate_cover_image(
    cover_html: str | Path, output_png: str | Path, *, chrome_bin: str | None = None
) -> None:
    """用 Chrome headless 把封面 HTML 转为 PNG。"""
    chrome = chrome_bin or _find_chrome()
    if chrome is None:
        logger.warning("未找到 Chrome，跳过封面图生成。")
        return
    cover_path = Path(cover_html)
    if not cover_path.exists():
        return
    png_path = Path(output_png)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.unlink(missing_ok=True)

    # HTML → 一页 A4 PDF
    cover_pdf = png_path.with_name(".cover_tmp.pdf")
    pdf_cmd = [
        chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
        f"--print-to-pdf={cover_pdf}", f"file://{cover_path}",
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
                logger.info("封面图生成: %s", png_path)
                return
        cover_pdf.unlink(missing_ok=True)

    # 回退：直接截图
    fallback = [
        chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
        "--default-background-color=00000000", f"--screenshot={png_path}",
        "--window-size=1240,1754", "--force-device-scale-factor=1",
        f"file://{cover_path}",
    ]
    completed = subprocess.run(fallback, check=False, capture_output=True, text=True)
    if completed.returncode == 0 and png_path.exists():
        logger.info("封面图生成（截图回退）: %s", png_path)
    else:
        logger.warning("封面图生成失败: %s", completed.stderr.strip())


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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


def _render(env: Environment, template_name: str, **context: Any) -> str:
    return env.get_template(template_name).render(**context)


def _join_markdown_parts(parts: list[str]) -> str:
    return "\n\n".join(part.strip() for part in parts if part.strip()) + "\n"


def _write_file(path: Path, content: str, generated_files: list[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    generated_files.append(str(path))
    logger.debug("已生成: %s", path)
