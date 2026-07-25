"""book-figure 图表资产扫描与替换 —— 纯写作分支，从文件系统扫描。"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass, field, replace
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
    """已生成的图表资产。"""
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
    source: str = "generated"
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
class PolishedFigureSource:
    """出版级精品图源文件。"""
    html_path: Path | None = None
    svg_path: Path | None = None
    png_path: Path | None = None


@dataclass(frozen=True)
class FigureExportResult:
    """收集并复制到导出目录的图表资产。"""
    figures_dir: str
    manifest: str
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
# Spec scanning (no BookState dependency)
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
# Manifest / Polished asset matching
# ---------------------------------------------------------------------------

def _load_manifest_assets(manifest_path: Path) -> dict[tuple[int, int, str], FigureAsset]:
    """从 .data/figures/manifest.json 加载已生成图表资产索引。"""
    if not manifest_path.exists():
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    assets: dict[tuple[int, int, str], FigureAsset] = {}
    for raw in payload.get("generated", []):
        if not isinstance(raw, dict):
            continue
        try:
            asset = FigureAsset(
                chapter_id=int(raw["chapter_id"]),
                section_id=str(raw.get("section_id", "")),
                occurrence=int(raw["occurrence"]),
                figure_id=str(raw["figure_id"]),
                figure_type=str(raw["figure_type"]),
                title=str(raw["title"]),
                caption=str(raw["caption"]),
                svg_path=str(raw["svg_path"]),
                html_path=str(raw["html_path"]),
                png_path=str(raw["png_path"]),
                markdown_path=str(raw["markdown_path"]),
                body_hash=str(raw["body_hash"]),
                source=str(raw.get("source") or "generated"),
                quality_tier=str(raw.get("quality_tier") or "standard"),
            )
        except (KeyError, TypeError, ValueError):
            continue
        assets[(asset.chapter_id, asset.occurrence, asset.body_hash)] = asset
    return assets


def _resolve_polished_dir(project_dir: Path, illustrations: dict[str, Any]) -> Path:
    raw_dir = normalize_book_figure_scalar(
        illustrations.get("polished_assets_dir") or "book/figures/polished"
    )
    path = Path(raw_dir)
    if path.is_absolute():
        return path
    return project_dir / path


def _find_polished_source(spec: FigureSpec, polished_dir: Path) -> PolishedFigureSource | None:
    """在 polished assets 目录查找匹配的出版级图表。"""
    chapter_dir = polished_dir / f"chapter-{spec.chapter_id:02d}"
    stems = _polished_stem_candidates(spec)
    html_path = _first_existing(chapter_dir, stems, ".html")
    svg_path = _first_existing(chapter_dir, stems, ".svg")
    png_path = _first_existing(chapter_dir, stems, ".png")
    if html_path is None and svg_path is None and png_path is None:
        return None
    return PolishedFigureSource(html_path=html_path, svg_path=svg_path, png_path=png_path)


def _polished_stem_candidates(spec: FigureSpec) -> list[str]:
    """返回可能的 polished 资产文件名（不含扩展名）。"""
    fallback = _fallback_figure_id(spec.chapter_id, spec.occurrence)
    candidates = [
        f"{_safe_slug(spec.figure_id)}--occ-{spec.occurrence:02d}",
        spec.figure_id,
        _safe_slug(spec.figure_id),
        fallback,
    ]
    result: list[str] = []
    for c in candidates:
        normalized = str(c).strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _first_existing(chapter_dir: Path, stems: list[str], suffix: str) -> Path | None:
    for stem in stems:
        path = chapter_dir / f"{stem}{suffix}"
        if path.exists():
            return path
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
    project_dir: str | Path | None = None,
) -> FigureExportResult:
    """从手稿扫描 book-figure，匹配 polished/manifest 资产，复制 PNG 到导出目录。

    - 优先匹配 polished assets（book/figures/polished/）
    - 其次匹配 .data/figures/manifest.json 中的已生成资产
    - 未匹配的记录到 missing，不阻断构建
    """
    illustration_cfg = illustration_config or {}
    source_dir = Path(source_figures_dir)
    export_dir = Path(export_figures_dir)
    manifest_path = source_dir / "manifest.json"
    proj_dir = Path(project_dir) if project_dir else Path.cwd()
    polished_dir = _resolve_polished_dir(proj_dir, illustration_cfg)

    manifest_assets = _load_manifest_assets(manifest_path)
    scan_result = _scan_figure_specs_from_chapters(chapters, illustration_cfg)

    logger.info(
        "图表扫描: %d 个 book-figure, %d 个 manifest 资产, polished=%s",
        len(scan_result.specs), len(manifest_assets), polished_dir,
    )

    assets: list[FigureAsset] = []
    missing: list[FigureFailure] = list(scan_result.failed)

    for spec in scan_result.specs:
        polished_source = _find_polished_source(spec, polished_dir)
        manifest_asset = manifest_assets.get((spec.chapter_id, spec.occurrence, spec.body_hash))

        # 确定 PNG 来源：优先 polished PNG，其次 manifest PNG
        png_source: Path | None = None
        source_tag = "generated"
        quality = "standard"
        svg_path = ""
        html_path = ""

        if polished_source is not None:
            source_tag = "polished"
            quality = "publication"
            svg_path = str(polished_source.svg_path) if polished_source.svg_path else ""
            html_path = str(polished_source.html_path) if polished_source.html_path else ""
            # 优先用 polished 自带的 PNG
            if polished_source.png_path is not None:
                png_source = polished_source.png_path
            # 否则回退到 manifest PNG（body_hash 可能不匹配，但尽量用）
            elif manifest_asset is not None and Path(manifest_asset.png_path).exists():
                png_source = Path(manifest_asset.png_path)
        elif manifest_asset is not None and Path(manifest_asset.png_path).exists():
            png_source = Path(manifest_asset.png_path)

        if png_source is None:
            missing.append(FigureFailure(
                chapter_id=spec.chapter_id, section_id=spec.section_id,
                occurrence=spec.occurrence, figure_id=spec.figure_id,
                reason="缺少匹配的 PNG 资产（polished 和 manifest 均无 PNG）",
                body_hash=spec.body_hash,
            ))
            continue

        # 复制 PNG 到导出目录
        stem = png_source.stem
        chapter_export_dir = export_dir / f"chapter-{spec.chapter_id:02d}"
        chapter_export_dir.mkdir(parents=True, exist_ok=True)
        target_png = chapter_export_dir / f"{stem}.png"
        _copy_asset_file(png_source, target_png)
        markdown_path = f"figures/chapter-{spec.chapter_id:02d}/{stem}.png"

        assets.append(FigureAsset(
            chapter_id=spec.chapter_id, section_id=spec.section_id,
            occurrence=spec.occurrence, figure_id=spec.figure_id,
            figure_type=spec.figure_type, title=spec.title,
            caption=spec.caption,
            svg_path=svg_path,
            html_path=html_path,
            png_path=str(target_png),
            markdown_path=markdown_path,
            body_hash=spec.body_hash,
            source=source_tag,
            quality_tier=quality,
        ))

    if missing:
        logger.warning("图表资产缺失 %d 个（将保留 book-figure 原始块）:", len(missing))
        for m in missing[:5]:
            logger.warning("  第%d章 %s: %s", m.chapter_id, m.figure_id, m.reason)
        if len(missing) > 5:
            logger.warning("  ...还有 %d 个", len(missing) - 5)

    return FigureExportResult(
        figures_dir=str(export_dir),
        manifest=str(manifest_path),
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
