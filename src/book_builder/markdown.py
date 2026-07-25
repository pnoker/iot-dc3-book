"""输出模块：从手稿组装单文件 book.md。"""

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


def generate_markdown_output(
    chapters: dict[int, str],
    parts: list[PartConfig],
    cfg: AppConfig,
    output_dir: str | Path,
    *,
    figure_assets: list[FigureAsset] | None = None,
    cover_html: str | Path | None = None,
) -> dict[str, object]:
    """将全书内容组装为单文件 book.md，并生成封面图。

    最终产出：book.md（含图引用）+ cover.png。图表 PNG 由 collect_figure_assets
    复制到 output/figures/。不再生成层级化分章 MD 和 book_clean.md。
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

    sections: list[str] = []

    # 封面
    sections.append(_render(env, "cover.md.j2"))
    # 作者简介
    profile = cfg.author.get("profile")
    if profile:
        sections.append(_render(env, "author_profile.md.j2", profile=profile))
    # 序言 & 导读
    preface = cfg.author.get("preface")
    if preface:
        sections.append(_render(env, "preface.md.j2", preface=preface))
        sections.append(_render(env, "reading_guide.md.j2", preface=preface, parts=parts))
    # 目录
    sections.append(_render(env, "toc.md.j2", parts=parts))
    # 篇章章节
    for part in parts:
        sections.append(f"# {part.prefix}、{part.name}\n")
        for chapter in part.chapters:
            content = chapters.get(chapter.id)
            if content is None:
                logger.warning("第%d章(%s) 缺少手稿内容，已跳过", chapter.id, chapter.title)
                continue
            sections.append(replace_book_figures_with_images(
                content, chapter.id, assets, marker=figure_marker,
            ))
    # 附录
    sections.append(_render(env, "appendix.md.j2"))

    # 合成 book.md
    book_path = out / cfg.output.book_markdown
    _write_file(book_path, _join_markdown_parts(sections))

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
