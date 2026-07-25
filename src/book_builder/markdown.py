"""输出模块：从手稿组装出版稿 Markdown。"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from book_builder.config import AppConfig, PartConfig
from book_builder.figures import FigureAsset, replace_book_figures_with_images
from book_builder.log import get_logger
from book_builder.pdf import generate_cover_image

logger = get_logger("markdown")


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


def generate_markdown_output(
    chapters: dict[int, str],
    parts: list[PartConfig],
    cfg: AppConfig,
    output_dir: str | Path,
    *,
    figure_assets: list[FigureAsset] | None = None,
    cover_html: str | Path | None = None,
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
    if cover_html and Path(cover_html).exists():
        generate_cover_image(cover_html, out / "cover.png")

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


def _render(env: Environment, template_name: str, **context: Any) -> str:
    return env.get_template(template_name).render(**context)


def _join_markdown_parts(parts: list[str]) -> str:
    return "\n\n".join(part.strip() for part in parts if part.strip()) + "\n"


def _write_file(path: Path, content: str, generated_files: list[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    generated_files.append(str(path))
    logger.debug("已生成: %s", path)
