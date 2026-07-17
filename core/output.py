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
    return {"output_dir": str(out), "book_markdown": str(book_markdown), "files": generated_files}


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
