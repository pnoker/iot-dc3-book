"""输出模块：生成出版稿 Markdown，并通过 Pandoc 转换 Word。"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.figures import FigureAsset, replace_book_figures_with_images
from core.log import get_logger
from core.state import BookState

logger = get_logger("output")


@lru_cache(maxsize=1)
def get_template_environment() -> Environment:
    """返回 Markdown 输出模板环境。"""
    template_dir = Path(__file__).resolve().parent / "templates"
    return Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def generate_markdown_output(
        state: BookState,
        output_dir: str,
        cfg: dict[str, Any] | None = None,
        *,
        figure_assets: list[FigureAsset] | None = None,
) -> dict[str, object]:
    """
    将全书内容输出为层级化 Markdown 与单文件 Markdown。

    输出结构：
    output/
    ├── 00-封面.md
    ├── 01-作者简介.md
    ├── 02-序.md
    ├── 03-导读.md
    ├── 04-目录.md
    ├── 05-基础篇/
    │   ├── 01-xxx.md
    │   └── ...
    ├── 06-技术篇/
    ├── 07-应用篇/
    ├── 08-附录.md
    ├── 09-伏笔报告.md
    ├── 10-终审报告.md
    └── book.md
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    # 生成封面图（assets/cover.html → output/cover.png，供封面页引用）
    cover_html = out.parent / "assets" / "cover.html"
    if cover_html.exists():
        _generate_cover_image(cover_html, out / "cover.png")
    env = get_template_environment()
    cfg = cfg or {}
    output_cfg = cfg.get("output", {})
    if not isinstance(output_cfg, dict):
        output_cfg = {}
    book_markdown_name = str(output_cfg.get("book_markdown") or "book.md")
    illustration_cfg = cfg.get("style", {}).get("illustrations", {}) if isinstance(cfg.get("style"), dict) else {}
    figure_marker = str(illustration_cfg.get("marker") or "book-figure") if isinstance(illustration_cfg, dict) else "book-figure"
    assets = figure_assets or []

    manuscript_parts: list[str] = []
    generated_files: list[str] = []

    cover = _render(env, "cover.md.j2", state=state)
    _write_file(out / "00-封面.md", cover, generated_files)
    manuscript_parts.append(cover)

    author_cfg = cfg.get("author", {})
    profile = author_cfg.get("profile")
    if profile:
        author_profile = _render(env, "author_profile.md.j2", profile=profile)
        _write_file(out / "01-作者简介.md", author_profile, generated_files)
        manuscript_parts.append(author_profile)

    preface = author_cfg.get("preface")
    if preface:
        preface_markdown = _render(env, "preface.md.j2", preface=preface)
        reading_guide = _render(env, "reading_guide.md.j2", preface=preface, state=state)
        _write_file(out / "02-序.md", preface_markdown, generated_files)
        _write_file(out / "03-导读.md", reading_guide, generated_files)
        manuscript_parts.extend([preface_markdown, reading_guide])

    toc_content = state.toc_markdown or _render(env, "toc.md.j2", state=state)
    _write_file(out / "04-目录.md", toc_content, generated_files)
    manuscript_parts.append(toc_content)

    part_dirs = ["05-基础篇", "06-技术篇", "07-应用篇"]
    for part_idx, part in enumerate(state.parts):
        dir_name = part_dirs[part_idx] if part_idx < len(part_dirs) else f"{part_idx + 1:02d}-{part.name}"
        part_dir = out / dir_name
        part_dir.mkdir(parents=True, exist_ok=True)
        manuscript_parts.append(f"# {part.prefix}、{part.name}\n")
        for chapter in part.chapters:
            content = state.get_chapter_content(chapter.id)
            if content:
                filename = f"{chapter.id:02d}-{chapter.title}.md"
                chapter_markdown = replace_book_figures_with_images(
                    content.markdown,
                    chapter.id,
                    assets,
                    marker=figure_marker,
                    image_prefix="../",
                )
                book_chapter_markdown = replace_book_figures_with_images(
                    content.markdown,
                    chapter.id,
                    assets,
                    marker=figure_marker,
                )
                _write_file(part_dir / filename, chapter_markdown, generated_files)
                manuscript_parts.append(book_chapter_markdown)

    appendix = _render(env, "appendix.md.j2")
    _write_file(out / "08-附录.md", appendix, generated_files)
    manuscript_parts.append(appendix)
    _write_file(
        out / "09-伏笔报告.md",
        _render(
            env,
            "foreshadow_report.md.j2",
            state=state,
            resolved_count=sum(1 for item in state.foreshadows if item.status == "resolved"),
        ),
        generated_files,
    )

    if state.final_report:
        _write_file(out / "10-终审报告.md", state.final_report, generated_files)

    book_markdown = out / book_markdown_name
    book_content = _join_markdown_parts(manuscript_parts)
    _write_file(book_markdown, book_content, generated_files)
    # 同时导出去除 pandoc 图片属性(如 {width=15cm})的 clean 版，便于普通 markdown 预览
    clean_content = re.sub(r"(!\[[^\]]*\]\([^\)]*\))\s*\{[^}]*\}", r"\1", book_content)
    _write_file(out / "book_clean.md", clean_content, generated_files)

    logger.info("输出完成: %s", out)
    return {"output_dir": str(out), "book_markdown": str(book_markdown), "book_clean": str(out / "book_clean.md"), "files": generated_files}


def generate_word_output(
        markdown_file: str | Path,
        word_file: str | Path,
        *,
        reference_docx: str | Path | None = None,
        pandoc_bin: str = "pandoc",
        toc: bool = True,
        toc_depth: int = 3,
) -> str:
    """使用 Pandoc 将单文件 Markdown 转为 Word docx。

    toc 启用时，先移除 book.md 中手写的静态 ``# 目录`` 段，再由 pandoc
    ``--toc`` 生成带页码、可右键更新的 Word 目录域，避免两份目录重复。
    """
    markdown_path = Path(markdown_file)
    if not markdown_path.exists():
        raise FileNotFoundError(f"Markdown 文件不存在: {markdown_path}")
    resolved_pandoc = shutil.which(pandoc_bin)
    if resolved_pandoc is None:
        raise RuntimeError("未找到 pandoc，无法生成 Word。请先安装 pandoc，或在 output.pandoc_bin 配置可执行文件路径。")

    word_path = Path(word_file)
    word_path.parent.mkdir(parents=True, exist_ok=True)

    src_path = markdown_path
    if toc:
        cleaned = _strip_static_toc(markdown_path.read_text(encoding="utf-8"))
        src_path = word_path.parent / ".book_for_word.md"
        src_path.write_text(cleaned, encoding="utf-8")

    cmd = [
        resolved_pandoc,
        str(src_path),
        "--from",
        "markdown+pipe_tables+fenced_code_blocks+yaml_metadata_block",
        "--to",
        "docx",
        "--output",
        str(word_path),
        "--resource-path",
        os.pathsep.join([str(markdown_path.parent), str(markdown_path.parent.parent)]),
    ]
    if toc:
        cmd.extend(["--toc", f"--toc-depth={toc_depth}"])
    if reference_docx:
        reference_path = Path(reference_docx)
        if not reference_path.exists():
            raise FileNotFoundError(f"Word 样式模板不存在: {reference_path}")
        cmd.extend(["--reference-doc", str(reference_path)])

    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if toc and src_path != markdown_path and src_path.exists():
        src_path.unlink()
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"Pandoc 生成 Word 失败: {stderr}")
    logger.info("Word 输出完成: %s", word_path)
    return str(word_path)


def _strip_static_toc(markdown_text: str) -> str:
    """移除手写的 ``# 目录`` 静态块，避免与 pandoc ``--toc`` 生成的目录域重复。

    逐行扫描时跟踪 ``\\`\\`\\``` 代码围栏，只在正文识别一级标题，避免误删
    代码块里以 ``#`` 开头的注释。
    """
    lines = markdown_text.split("\n")
    out: list[str] = []
    in_code = False
    skipping = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            out.append(line)
            continue
        if skipping:
            # 跳过目录内容，直到下一个正文一级标题
            if not in_code and stripped.startswith("# ") and stripped != "# 目录":
                skipping = False
                out.append(line)
            continue
        if not in_code and stripped == "# 目录":
            skipping = True
            continue
        out.append(line)
    return "\n".join(out)


def _render(env: Environment, template_name: str, **context: Any) -> str:
    return env.get_template(template_name).render(**context)


def _join_markdown_parts(parts: list[str]) -> str:
    return "\n\n".join(part.strip() for part in parts if part.strip()) + "\n"


def _write_file(path: Path, content: str, generated_files: list[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    generated_files.append(str(path))
    logger.debug("已生成: %s", path)


def _find_chrome() -> str | None:
    """查找本机 Chromium 内核浏览器可执行文件（Chrome/Edge/Brave/Chromium）。"""
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


def generate_pdf_output(
        markdown_file: str | Path,
        pdf_file: str | Path,
        *,
        css_file: str | Path | None = None,
        chrome_bin: str | None = None,
        pandoc_bin: str = "pandoc",
        cover_html: str | Path | None = None,
) -> str | None:
    """从 Markdown 生成 PDF：pandoc 转 HTML → Chrome headless 转 PDF。

    若提供 cover_html，则先将设计封面单独渲染为一页全幅 A4 PDF，再与正文
    PDF 合并为首页，避免 pandoc 自动标题页盖掉设计封面。
    无 Chrome/Edge 时跳过并警告（不报错），便于无浏览器环境跳过 PDF。
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

    cover_path = Path(cover_html) if cover_html else None
    has_cover = bool(cover_path and cover_path.exists())

    # 有设计封面时，剥离正文 markdown 开头的 ![](cover.png) 引用，
    # 避免封面图在正文首页重复出现（封面已单独成页）。
    pandoc_input = markdown_path
    if has_cover:
        text = markdown_path.read_text(encoding="utf-8")
        stripped = re.sub(r"^\s*!\[[^\]]*\]\(cover\.png\)\s*\n", "", text, count=1)
        if stripped != text:
            pandoc_input = pdf_path.with_name(".book_body.md")
            pandoc_input.write_text(stripped, encoding="utf-8")

    # pandoc: markdown → html（standalone，附 CSS）。
    # 不注入 title 元数据——避免 pandoc 生成的标题页盖掉设计封面。
    cmd = [
        resolved_pandoc, str(pandoc_input), "-o", str(html_path),
        "--standalone", "--from", "markdown+pipe_tables+fenced_code_blocks",
    ]
    css_cwd = None
    if css_file and Path(css_file).exists():
        cmd += ["--css", Path(css_file).name]
        css_cwd = str(Path(css_file).parent)
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True, cwd=css_cwd)
    if completed.returncode != 0:
        raise RuntimeError(f"pandoc 生成 HTML 失败: {completed.stderr.strip()}")

    # 若有设计封面，正文 PDF 先写到临时文件，最后与封面合并
    body_pdf = pdf_path.with_name(".book_body.pdf") if has_cover else pdf_path

    # Chrome headless: 正文 html → pdf
    chrome_cmd = [
        chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
        f"--print-to-pdf={body_pdf}", f"file://{html_path}",
    ]
    completed = subprocess.run(chrome_cmd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"Chrome 生成 PDF 失败: {completed.stderr.strip()}")

    # 设计封面：单独渲染为一页全幅 A4 PDF，再与正文合并为首页
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
            except Exception as exc:  # 合并失败则退回仅正文 PDF
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

    # 清理剥离封面引用后的临时正文 md
    if pandoc_input != markdown_path:
        pandoc_input.unlink(missing_ok=True)

    logger.info("PDF 输出完成: %s", pdf_path)
    return str(pdf_path)


def _generate_cover_image(cover_html: str | Path, output_png: str | Path, *, chrome_bin: str | None = None) -> None:
    """用 Chrome headless 把封面 HTML 转为 PNG。

    先 print-to-pdf（`@page A4` 精确分页、无留白），再转 PNG——比 --screenshot
    的视口截图更可靠，不受视口高度与 body 高度不吻合导致的底部留白影响。
    转 PNG 优先用 pypdf 渲染，退化到 sips（macOS）；均不可用时回退到 --screenshot。
    无 Chrome 时跳过。
    """
    chrome = chrome_bin or _find_chrome()
    if chrome is None:
        logger.warning("未找到 Chrome，跳过封面图生成。")
        return
    cover_path = Path(cover_html)
    if not cover_path.exists():
        return
    png_path = Path(output_png)
    png_path.parent.mkdir(parents=True, exist_ok=True)

    # 1) HTML → 一页 A4 PDF（精确分页，无留白）
    cover_pdf = png_path.with_name(".cover_tmp.pdf")
    pdf_cmd = [
        chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
        f"--print-to-pdf={cover_pdf}", f"file://{cover_path}",
    ]
    pdf_done = subprocess.run(pdf_cmd, check=False, capture_output=True, text=True)

    # 2) PDF → PNG（sips 在 macOS 上可直接转）
    if pdf_done.returncode == 0 and cover_pdf.exists():
        sips = shutil.which("sips")
        if sips:
            conv = subprocess.run(
                [sips, "-s", "format", "png", str(cover_pdf), "--out", str(png_path)],
                check=False, capture_output=True, text=True,
            )
            cover_pdf.unlink(missing_ok=True)
            if conv.returncode == 0 and png_path.exists():
                logger.info("封面图生成: %s", png_path)
                return
        cover_pdf.unlink(missing_ok=True)

    # 3) 回退：直接截图（可能有留白，但保证有产物）
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
