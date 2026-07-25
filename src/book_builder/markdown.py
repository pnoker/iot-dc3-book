"""输出模块：从手稿组装层级化分章 MD 与单文件 book.md。"""

from __future__ import annotations

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


def assemble_book_markdown(
    chapters: dict[int, str],
    parts: list[PartConfig],
    cfg: AppConfig,
    figure_assets: list[FigureAsset] | None,
    *,
    until_chapter: int | None = None,
) -> str:
    """组装单文件合集 markdown（用直接路径引用图）。

    until_chapter 设定时只包含该章及之前的章节、且不含附录（用于样张）。
    无入选章节的篇会跳过篇标题。
    """
    env = get_template_environment()
    figure_marker = str(cfg.style.illustrations.marker or "book-figure")
    assets = figure_assets or []
    sections: list[str] = []

    sections.append(_render(env, "cover.md.j2"))
    profile = cfg.author.get("profile")
    if profile:
        sections.append(_render(env, "author_profile.md.j2", profile=profile))
    preface = cfg.author.get("preface")
    if preface:
        sections.append(_render(env, "preface.md.j2", preface=preface))
        sections.append(_render(env, "reading_guide.md.j2", preface=preface, parts=parts))
    sections.append(_render(env, "toc.md.j2", parts=parts))

    for part in parts:
        part_chapters = [
            c for c in part.chapters
            if until_chapter is None or c.id <= until_chapter
        ]
        if not part_chapters:
            continue
        sections.append(f"# {part.prefix}、{part.name}\n")
        for chapter in part_chapters:
            content = chapters.get(chapter.id)
            if content is None:
                continue
            sections.append(replace_book_figures_with_images(
                content, chapter.id, assets, marker=figure_marker,
            ))

    if until_chapter is None:
        sections.append(_render(env, "appendix.md.j2"))

    return _join_markdown_parts(sections)


def generate_markdown_output(
    chapters: dict[int, str],
    parts: list[PartConfig],
    cfg: AppConfig,
    output_dir: str | Path,
    *,
    figure_assets: list[FigureAsset] | None = None,
    cover_html: str | Path | None = None,
) -> dict[str, object]:
    """将全书内容输出为层级化分章 MD 与单文件 book.md，并生成封面图。

    层级文件用 `../` 前缀引用图片，book.md 用直接路径。
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 封面图
    if cover_html and Path(cover_html).exists():
        generate_cover_image(cover_html, out / "cover.png")

    env = get_template_environment()
    figure_marker = str(cfg.style.illustrations.marker or "book-figure")
    assets = figure_assets or []

    # 层级化分章 MD（用 ../ 前缀引用图片）
    _write_file(out / "00-封面.md", _render(env, "cover.md.j2"))
    profile = cfg.author.get("profile")
    if profile:
        _write_file(out / "01-作者简介.md", _render(env, "author_profile.md.j2", profile=profile))
    preface = cfg.author.get("preface")
    if preface:
        _write_file(out / "02-序.md", _render(env, "preface.md.j2", preface=preface))
        _write_file(out / "03-导读.md", _render(env, "reading_guide.md.j2", preface=preface, parts=parts))
    _write_file(out / "04-目录.md", _render(env, "toc.md.j2", parts=parts))

    part_start_index = 5  # 前 4 个序号已用（封面/作者/序+导读/目录）
    for part_idx, part in enumerate(parts):
        dir_name = f"{part_idx + part_start_index:02d}-{part.name}"
        part_dir = out / dir_name
        part_dir.mkdir(parents=True, exist_ok=True)
        for chapter in part.chapters:
            content = chapters.get(chapter.id)
            if content is None:
                logger.warning("第%d章(%s) 缺少手稿内容，已跳过", chapter.id, chapter.title)
                continue
            filename = f"{chapter.id:02d}-{chapter.title}.md"
            chapter_markdown = replace_book_figures_with_images(
                content, chapter.id, assets, marker=figure_marker, image_prefix="../",
            )
            _write_file(part_dir / filename, chapter_markdown)

    _write_file(out / "08-附录.md", _render(env, "appendix.md.j2"))

    # 单文件合集 book.md
    book_path = out / cfg.output.book_markdown
    _write_file(book_path, assemble_book_markdown(chapters, parts, cfg, assets))

    logger.info("Markdown 输出完成: %s", book_path)
    return {"output_dir": str(out), "book_markdown": str(book_path)}


def _render(env: Environment, template_name: str, **context: Any) -> str:
    return env.get_template(template_name).render(**context)


def _join_markdown_parts(parts: list[str]) -> str:
    return "\n\n".join(part.strip() for part in parts if part.strip()) + "\n"


def _write_file(path: Path, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.debug("已生成: %s", path)
