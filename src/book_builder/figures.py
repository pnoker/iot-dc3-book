"""book-figure 图表资产扫描与替换 —— 纯写作分支，从文件系统扫描。"""

from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from book_builder.markdown_assets import (
    BookFigureBlock,
    book_figure_string_list,
    iter_book_figure_blocks,
    normalize_book_figure_scalar,
    parse_book_figure_payload,
)
from book_builder.log import get_logger

logger = get_logger("figures")

_DEFAULT_REQUIRED_FIELDS = [
    "id", "type", "title", "purpose", "layout", "elements",
    "relationships", "legend", "caption", "render_notes",
]
_DEFAULT_ALLOWED_TYPES = [
    "architecture", "sequence", "flowchart", "dataflow",
    "pyramid", "layered", "topology", "lifecycle", "matrix", "timeline",
]
_PUBLICATION_IMAGE_WIDTH = "15cm"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FigureSpec:
    """规范化后的图表规格。"""
    chapter_id: int
    section_id: str
    occurrence: int
    figure_id: str
    figure_type: str
    title: str
    purpose: str
    layout: str
    elements: list[str]
    relationships: list[str]
    legend: list[str]
    caption: str
    render_notes: str
    body_hash: str


@dataclass(frozen=True)
class FigureAsset:
    """已匹配的图表资产。"""
    chapter_id: int
    section_id: str
    occurrence: int
    figure_id: str
    figure_type: str
    title: str
    caption: str
    svg_path: str
    html_path: str
    png_path: str
    markdown_path: str
    body_hash: str
    source: str = "filesystem"
    quality_tier: str = "standard"


@dataclass(frozen=True)
class FigureFailure:
    """无法匹配的图表规格。"""
    chapter_id: int
    section_id: str
    occurrence: int
    figure_id: str
    reason: str
    body_hash: str


@dataclass(frozen=True)
class FigureScanResult:
    """从章节合稿中解析出的图表规格。"""
    specs: list[FigureSpec]
    failed: list[FigureFailure]


@dataclass(frozen=True)
class FigureExportResult:
    """收集并复制到导出目录的图表资产。"""
    figures_dir: str
    assets: list[FigureAsset]
    missing: list[FigureFailure]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _fallback_figure_id(chapter_id: int, occurrence: int) -> str:
    return f"fig-{chapter_id:02d}-{occurrence:02d}"


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-._")
    return slug.lower()


def _section_id_for_offset(markdown: str, offset: int, chapter_id: int) -> str:
    pattern = re.compile(rf"^#{{2,6}}\s+({chapter_id}\.\d+\.\d+)\b", re.MULTILINE)
    section_id = ""
    for match in pattern.finditer(markdown[:offset]):
        section_id = match.group(1)
    return section_id


def _copy_asset_file(source: Path, target: Path) -> None:
    if source.resolve() == target.resolve():
        return
    shutil.copyfile(source, target)


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


# ---------------------------------------------------------------------------
# Spec scanning
# ---------------------------------------------------------------------------

def _scan_figure_specs_from_chapters(
    chapters: dict[int, str],
    illustration_config: dict[str, Any],
) -> FigureScanResult:
    """扫描所有章节 markdown 中的 book-figure 代码块。"""
    marker = str(illustration_config.get("marker") or "book-figure")
    required_fields = _string_list(illustration_config.get("required_fields")) or _DEFAULT_REQUIRED_FIELDS
    allowed_types = {
        normalize_book_figure_scalar(item).lower()
        for item in (_string_list(illustration_config.get("allowed_types")) or _DEFAULT_ALLOWED_TYPES)
    }

    specs: list[FigureSpec] = []
    failed: list[FigureFailure] = []
    for chapter_id, markdown in chapters.items():
        for occurrence, block in enumerate(iter_book_figure_blocks(markdown, marker), start=1):
            body_hash = _hash_text(block.body)
            section_id = _section_id_for_offset(markdown, block.start, chapter_id)
            spec, reason = _parse_figure_spec(
                block, chapter_id=chapter_id, section_id=section_id,
                occurrence=occurrence, body_hash=body_hash,
                required_fields=required_fields, allowed_types=allowed_types,
            )
            if spec is None:
                failed.append(FigureFailure(
                    chapter_id=chapter_id, section_id=section_id,
                    occurrence=occurrence,
                    figure_id=_fallback_figure_id(chapter_id, occurrence),
                    reason=reason, body_hash=body_hash,
                ))
                continue
            specs.append(spec)
    return FigureScanResult(specs=specs, failed=failed)


def _parse_figure_spec(
    block: BookFigureBlock,
    *,
    chapter_id: int,
    section_id: str,
    occurrence: int,
    body_hash: str,
    required_fields: list[str],
    allowed_types: set[str],
) -> tuple[FigureSpec | None, str]:
    """解析单个 book-figure YAML 块为 FigureSpec。"""
    payload, reason = parse_book_figure_payload(block.body)
    if payload is None:
        return None, reason
    missing = [f for f in required_fields if f not in payload or payload.get(f) in (None, "", [])]
    if missing:
        return None, "缺少字段: " + ", ".join(missing)

    figure_type = normalize_book_figure_scalar(payload.get("type") or "").lower()
    if figure_type not in allowed_types:
        return None, f"不支持的图表类型: {figure_type}"

    figure_id = (
        _safe_slug(normalize_book_figure_scalar(payload.get("id") or ""))
        or _fallback_figure_id(chapter_id, occurrence)
    )
    return (
        FigureSpec(
            chapter_id=chapter_id,
            section_id=section_id,
            occurrence=occurrence,
            figure_id=figure_id,
            figure_type=figure_type,
            title=normalize_book_figure_scalar(payload.get("title") or figure_id),
            purpose=normalize_book_figure_scalar(payload.get("purpose") or ""),
            layout=normalize_book_figure_scalar(payload.get("layout") or ""),
            elements=book_figure_string_list(payload.get("elements")),
            relationships=book_figure_string_list(payload.get("relationships")),
            legend=book_figure_string_list(payload.get("legend")),
            caption=normalize_book_figure_scalar(payload.get("caption") or ""),
            render_notes=normalize_book_figure_scalar(payload.get("render_notes") or ""),
            body_hash=body_hash,
        ),
        "",
    )


# ---------------------------------------------------------------------------
# Asset matching
# ---------------------------------------------------------------------------

def _find_figure_png_by_id(
    source_figures_dir: Path, chapter_id: int, figure_id: str
) -> Path | None:
    """按 figure_id 在 figures/chapter-XX/ 查找同名 PNG。"""
    chapter_dir = source_figures_dir / f"chapter-{chapter_id:02d}"
    for stem in (figure_id, _safe_slug(figure_id)):
        png = chapter_dir / f"{stem}.png"
        if png.exists():
            return png
    return None


# ---------------------------------------------------------------------------
# Asset collection
# ---------------------------------------------------------------------------

def collect_figure_assets(
    chapters: dict[int, str],
    export_figures_dir: str | Path,
    *,
    source_figures_dir: str | Path,
    illustration_config: dict[str, Any] | None = None,
) -> FigureExportResult:
    """从手稿扫描 book-figure，按 figure_id 匹配同名 PNG，复制到导出目录。

    匹配规则：在 figures/chapter-XX/ 下查找与 figure_id 同名的 PNG。
    未匹配的不阻断构建，原 book-figure 块保留。
    """
    illustration_cfg = illustration_config or {}
    source_dir = Path(source_figures_dir)
    export_dir = Path(export_figures_dir)
    scan_result = _scan_figure_specs_from_chapters(chapters, illustration_cfg)
    logger.info("图表扫描: %d 个 book-figure", len(scan_result.specs))

    assets: list[FigureAsset] = []
    missing: list[FigureFailure] = list(scan_result.failed)

    for spec in scan_result.specs:
        png_source = _find_figure_png_by_id(source_dir, spec.chapter_id, spec.figure_id)
        if png_source is None:
            missing.append(FigureFailure(
                chapter_id=spec.chapter_id, section_id=spec.section_id,
                occurrence=spec.occurrence, figure_id=spec.figure_id,
                reason=f"缺少同名 PNG: figures/chapter-{spec.chapter_id:02d}/{spec.figure_id}.png",
                body_hash=spec.body_hash,
            ))
            continue

        stem = png_source.stem
        chapter_export_dir = export_dir / f"chapter-{spec.chapter_id:02d}"
        chapter_export_dir.mkdir(parents=True, exist_ok=True)
        target_png = chapter_export_dir / f"{stem}.png"
        _copy_asset_file(png_source, target_png)
        markdown_path = f"figures/chapter-{spec.chapter_id:02d}/{stem}.png"

        assets.append(FigureAsset(
            chapter_id=spec.chapter_id, section_id=spec.section_id,
            occurrence=spec.occurrence, figure_id=spec.figure_id,
            figure_type=spec.figure_type, title=spec.title, caption=spec.caption,
            svg_path="", html_path="",
            png_path=str(target_png),
            markdown_path=markdown_path,
            body_hash=spec.body_hash,
        ))

    if missing:
        logger.warning("图表资产缺失 %d 个（将保留 book-figure 原始块）:", len(missing))
        for m in missing[:5]:
            logger.warning("  第%d章 %s: %s", m.chapter_id, m.figure_id, m.reason)
        if len(missing) > 5:
            logger.warning("  ...还有 %d 个", len(missing) - 5)

    return FigureExportResult(
        figures_dir=str(export_dir),
        assets=assets,
        missing=missing,
    )


# ---------------------------------------------------------------------------
# Markdown replacement
# ---------------------------------------------------------------------------

def replace_book_figures_with_images(
    markdown: str,
    chapter_id: int,
    assets: list[FigureAsset],
    *,
    marker: str = "book-figure",
    image_prefix: str = "",
) -> str:
    """把章节正文中的 book-figure 规格块替换为 PNG 图片引用。"""
    by_occurrence = {(asset.chapter_id, asset.occurrence): asset for asset in assets}
    blocks = iter_book_figure_blocks(markdown, marker)
    if not blocks:
        return markdown

    parts: list[str] = []
    cursor = 0
    for occurrence, block in enumerate(blocks, start=1):
        parts.append(markdown[cursor:block.start])
        asset = by_occurrence.get((chapter_id, occurrence))
        if asset is None:
            parts.append(markdown[block.start:block.end])
        else:
            image_path = f"{image_prefix}{asset.markdown_path}"
            parts.append(
                f"![{asset.title}]({image_path}){{width={_PUBLICATION_IMAGE_WIDTH}}}\n\n*{asset.caption}*"
            )
        cursor = block.end
    parts.append(markdown[cursor:])
    return "".join(parts)
