"""篇章扉页 HTML 渲染。"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from book_builder.config import PartConfig
from book_builder.figure_renderer import _ChromeSession
from book_builder.log import get_logger

logger = get_logger("dividers")


@dataclass(frozen=True)
class DividerSpec:
    divider_id: str
    source: Path
    context: dict[str, Any]


def render_divider_assets(
    parts: list[PartConfig],
    source_dir: str | Path,
    output_dir: str | Path,
    *,
    until_chapter: int | None = None,
    chrome_bin: str | None = None,
    export_width: int = 2480,
) -> dict[str, Path]:
    source_root = Path(source_dir)
    if not source_root.is_dir():
        raise FileNotFoundError(f"篇章扉页源目录不存在: {source_root}")
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    specs = _build_specs(parts, source_root, until_chapter)
    environment = Environment(
        loader=FileSystemLoader(source_root),
        autoescape=select_autoescape(enabled_extensions=("html",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    session = _ChromeSession(chrome_bin)
    assets: dict[str, Path] = {}
    try:
        for spec in specs:
            if not spec.source.exists():
                raise FileNotFoundError(f"缺少篇章扉页 HTML: {spec.source}")
            rendered = environment.get_template(spec.source.name).render(**spec.context)
            temporary_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    suffix=".html",
                    prefix=f".{spec.divider_id}-",
                    dir=source_root,
                    delete=False,
                ) as temporary:
                    temporary.write(rendered)
                    temporary_path = Path(temporary.name)
                output = output_root / f"{spec.divider_id}.png"
                result = session.render(temporary_path, output, export_width)
                if result.height != 3508:
                    raise RuntimeError(
                        f"篇章扉页尺寸异常: {spec.divider_id}，"
                        f"预期 {export_width}x3508，实际 {result.width}x{result.height}"
                    )
                assets[spec.divider_id] = output
                logger.info("扉页导出: %s (%dx%d)", output, result.width, result.height)
            finally:
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)
    finally:
        session.close()
    return assets


def _build_specs(
    parts: list[PartConfig],
    source_root: Path,
    until_chapter: int | None,
) -> list[DividerSpec]:
    themes = ("foundation", "technology", "application")
    specs: list[DividerSpec] = []
    for part_index, part in enumerate(parts, start=1):
        chapters = [
            chapter
            for chapter in part.chapters
            if until_chapter is None or chapter.id <= until_chapter
        ]
        if not chapters:
            continue
        theme = themes[(part_index - 1) % len(themes)]
        part_id = f"part-{part_index:02d}"
        specs.append(DividerSpec(
            divider_id=part_id,
            source=source_root / f"{part_id}.html",
            context={
                "kind": "part",
                "theme": theme,
                "number": f"{part_index:02d}",
                "label": part.prefix,
                "english_label": f"PART {part_index:02d}",
                "title": part.name,
                "title_main": part.name,
                "title_sub": "",
                "description": part.description,
            },
        ))
        for chapter in chapters:
            title_main, _, title_sub = chapter.title.partition("：")
            chapter_id = f"chapter-{chapter.id:02d}"
            specs.append(DividerSpec(
                divider_id=chapter_id,
                source=source_root / f"{chapter_id}.html",
                context={
                    "kind": "chapter",
                    "theme": theme,
                    "number": f"{chapter.id:02d}",
                    "label": f"第{chapter.id}章",
                    "english_label": f"CHAPTER {chapter.id:02d}",
                    "title": chapter.title,
                    "title_main": title_main,
                    "title_sub": title_sub,
                    "description": chapter.description,
                },
            ))
    return specs
