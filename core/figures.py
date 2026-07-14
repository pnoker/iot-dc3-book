"""`book-figure` 图表规格渲染流水线。"""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
import shutil
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Protocol
from xml.etree import ElementTree

from core.log import get_logger
from core.markdown_assets import (
    BookFigureBlock,
    book_figure_string_list,
    iter_book_figure_blocks,
    normalize_book_figure_scalar,
    parse_book_figure_payload,
)
from core.state import BookState

logger = get_logger("figures")

_DEFAULT_REQUIRED_FIELDS = [
    "id",
    "type",
    "title",
    "purpose",
    "layout",
    "elements",
    "relationships",
    "legend",
    "caption",
    "render_notes",
]
_DEFAULT_ALLOWED_TYPES = [
    "architecture",
    "sequence",
    "flowchart",
    "dataflow",
    "pyramid",
    "layered",
    "topology",
    "lifecycle",
    "matrix",
    "timeline",
]
_DEFAULT_PALETTE = {
    "canvas": "#F8FAFC",
    "panel": "#FFFFFF",
    "primary": "#2563EB",
    "secondary": "#0F766E",
    "accent": "#F97316",
    "neutral": "#475569",
    "line": "#94A3B8",
    "text": "#0F172A",
    "success": "#16A34A",
    "warning": "#D97706",
    "danger": "#DC2626",
}
_TEMPLATE_RENDERER_VERSION = "template-html-svg-v2"
_AI_RENDERER_VERSION = "ai-html-svg-v2"
_FORBIDDEN_SVG_TAGS = {"script", "foreignobject", "iframe", "object", "embed", "audio", "video", "canvas", "image"}
_FORBIDDEN_SVG_VALUE_RE = re.compile(r"(?:javascript:|data:|https?://|@import)", re.I)
_FONT_FAMILY = "Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif"
_PUBLICATION_CANVAS_WIDTH = 1200
_PUBLICATION_CANVAS_HEIGHT = 760
_PUBLICATION_CANVAS_PADDING = 24
_PUBLICATION_IMAGE_WIDTH = "15cm"
_GENERIC_NODE_LABEL_RE = re.compile(r"^(?:节点|决策节点|判断节点|处理节点|计算节点|执行节点|开始节点|结束状态|输入数据源|输出节点|最左侧|最右侧|左侧|右侧)\d*$")
_CHINESE_QUOTE_RE = re.compile(r"[‘’'\"“”]([^‘’'\"“”]{3,80})[‘’'\"“”]")
_ASCII_ROLE_MAP = {
    "container": "",
    "service": "服务能力",
    "user": "参与者",
    "core_platform": "核心平台",
    "platform": "平台能力",
    "database": "数据存储",
    "gateway": "接入网关",
}


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
    audience_takeaway: str = ""
    visual_focus: str = ""
    design_level: str = ""
    components: list[dict[str, str]] = field(default_factory=list)
    connections: list[dict[str, str]] = field(default_factory=list)
    regions: list[dict[str, str]] = field(default_factory=list)
    callouts: list[str] = field(default_factory=list)
    visual_constraints: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FigureDesign:
    """AI 图表设计器输出。

    html 为空表示 LLM 直出失败、走了本地语义蓝图兜底，此时由管线用模板外壳包裹 svg。
    """

    svg: str
    html: str = ""
    notes: str = ""


class FigureDesigner(Protocol):
    """面向 `book-figure` 的出版级 SVG 设计器协议。"""

    def design(self, spec: FigureSpec, *, palette: dict[str, str], feedback: str = "") -> FigureDesign:
        """根据图表规格生成完整 SVG。"""


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
    """无法渲染的图表规格。"""

    chapter_id: int
    section_id: str
    occurrence: int
    figure_id: str
    reason: str
    body_hash: str


@dataclass(frozen=True)
class FigureBuildResult:
    """图表构建结果。"""

    output_dir: str
    figures_dir: str
    manifest: str
    generated: list[FigureAsset]
    failed: list[FigureFailure]
    renderer_version: str = _TEMPLATE_RENDERER_VERSION
    reused_count: int = 0
    polished_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "output_dir": self.output_dir,
            "figures_dir": self.figures_dir,
            "manifest": self.manifest,
            "renderer_version": self.renderer_version,
            "generated_count": len(self.generated),
            "reused_count": self.reused_count,
            "polished_count": self.polished_count,
            "failed_count": len(self.failed),
            "generated": [asdict(asset) for asset in self.generated],
            "failed": [asdict(failure) for failure in self.failed],
        }


@dataclass(frozen=True)
class FigureScanResult:
    """从章节合稿中解析出的图表规格。"""

    specs: list[FigureSpec]
    failed: list[FigureFailure]


@dataclass(frozen=True)
class PolishedFigureSource:
    """人工/外部精修后的出版级图表源文件。"""

    html_path: Path | None = None
    svg_path: Path | None = None
    png_path: Path | None = None


def scan_figure_specs(state: BookState, *, illustrations: dict[str, Any] | None = None) -> FigureScanResult:
    """扫描章节合稿中的最终入书图表规格。"""
    illustration_cfg = illustrations or state.style.illustrations or {}
    marker = str(illustration_cfg.get("marker") or "book-figure")
    required_fields = _string_list(illustration_cfg.get("required_fields")) or _DEFAULT_REQUIRED_FIELDS
    allowed_types = {
        normalize_book_figure_scalar(item).lower()
        for item in (_string_list(illustration_cfg.get("allowed_types")) or _DEFAULT_ALLOWED_TYPES)
    }
    specs: list[FigureSpec] = []
    failed: list[FigureFailure] = []
    for chapter in state.get_all_chapters_flat():
        content = state.get_chapter_content(chapter.id)
        if content is None:
            continue
        for occurrence, block in enumerate(iter_book_figure_blocks(content.markdown, marker), start=1):
            body_hash = _hash_text(block.body)
            section_id = _section_id_for_offset(content.markdown, block.start, chapter.id)
            spec, reason = _parse_figure_spec(
                block,
                chapter_id=chapter.id,
                section_id=section_id,
                occurrence=occurrence,
                body_hash=body_hash,
                required_fields=required_fields,
                allowed_types=allowed_types,
            )
            if spec is None:
                failed.append(
                    FigureFailure(
                        chapter_id=chapter.id,
                        section_id=section_id,
                        occurrence=occurrence,
                        figure_id=_fallback_figure_id(chapter.id, occurrence),
                        reason=reason,
                        body_hash=body_hash,
                    )
                )
                continue
            specs.append(spec)
    return FigureScanResult(specs=specs, failed=failed)


def build_figure_assets(
        state: BookState,
        output_dir: str | Path,
        *,
        illustrations: dict[str, Any] | None = None,
        png_renderer: str = "sips",
        designer: FigureDesigner | None = None,
        force: bool = False,
        project_dir: str | Path | None = None,
        require_polished: bool = False,
        figures_dir: str | Path | None = None,
) -> FigureBuildResult:
    """扫描全书 `book-figure` 并生成 HTML、SVG、PNG 图表资产。

    figures_dir 显式指定图表资产存储目录（如 .data/figures，权威存储）；
    未指定时沿用旧行为，落到 output_dir/figures。
    """
    out = Path(output_dir)
    figures_dir = Path(figures_dir) if figures_dir is not None else out / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    illustration_cfg = illustrations or state.style.illustrations or {}
    renderer = str(illustration_cfg.get("renderer") or "ai-html-svg")
    active_designer = designer if renderer == "ai-html-svg" else None
    renderer_version = _AI_RENDERER_VERSION if active_designer is not None else _TEMPLATE_RENDERER_VERSION
    palette = _figure_palette(illustration_cfg)
    min_polished_png_bytes = int(illustration_cfg.get("polished_min_png_bytes") or 0)
    polished_dir = _resolve_polished_assets_dir(project_dir, illustration_cfg)
    manifest_path = figures_dir / "manifest.json"
    reusable_assets = {} if force else _load_reusable_assets(manifest_path, renderer_version=renderer_version)
    scan_result = scan_figure_specs(state, illustrations=illustration_cfg)

    generated: list[FigureAsset] = []
    failed: list[FigureFailure] = list(scan_result.failed)
    reused_count = 0
    polished_count = 0
    used_file_stems: set[str] = set()
    for spec in scan_result.specs:
        polished_source = _find_polished_source(spec, polished_dir)
        if polished_source is not None:
            try:
                logger.info("💎 [图表] 使用精品图: 第%d章 %s", spec.chapter_id, spec.figure_id)
                asset = _write_polished_figure_asset(
                    spec,
                    figures_dir=figures_dir,
                    used_file_stems=used_file_stems,
                    source=polished_source,
                    min_png_bytes=min_polished_png_bytes,
                )
            except (RuntimeError, ValueError, OSError) as exc:
                logger.warning("❌ [图表] 精品图失败: 第%d章 %s - %s", spec.chapter_id, spec.figure_id, exc)
                failed.append(
                    FigureFailure(
                        chapter_id=spec.chapter_id,
                        section_id=spec.section_id,
                        occurrence=spec.occurrence,
                        figure_id=spec.figure_id,
                        reason=str(exc),
                        body_hash=spec.body_hash,
                    )
                )
                continue
            logger.info("✅ [图表] 精品图完成: %s", asset.png_path)
            generated.append(asset)
            polished_count += 1
            continue
        if require_polished:
            failed.append(
                FigureFailure(
                    chapter_id=spec.chapter_id,
                    section_id=spec.section_id,
                    occurrence=spec.occurrence,
                    figure_id=spec.figure_id,
                    reason=_missing_polished_reason(spec, polished_dir),
                    body_hash=spec.body_hash,
                )
            )
            continue
        reusable = reusable_assets.get((spec.chapter_id, spec.occurrence, spec.body_hash))
        if reusable is not None:
            logger.info("♻️ [图表] 复用缓存: 第%d章 %s", spec.chapter_id, spec.figure_id)
            generated.append(reusable)
            used_file_stems.add(Path(reusable.png_path).stem)
            reused_count += 1
            continue
        try:
            logger.info(
                "🎨 [图表] 生成: 第%d章 %s (%s)%s",
                spec.chapter_id,
                spec.figure_id,
                spec.figure_type,
                " AI" if active_designer is not None else " template",
            )
            asset = _write_figure_asset(
                spec,
                figures_dir=figures_dir,
                palette=palette,
                used_file_stems=used_file_stems,
                designer=active_designer,
            )
        except (RuntimeError, ValueError) as exc:
            logger.warning("❌ [图表] 失败: 第%d章 %s - %s", spec.chapter_id, spec.figure_id, exc)
            failed.append(
                FigureFailure(
                    chapter_id=spec.chapter_id,
                    section_id=spec.section_id,
                    occurrence=spec.occurrence,
                    figure_id=spec.figure_id,
                    reason=str(exc),
                    body_hash=spec.body_hash,
                )
            )
            continue
        logger.info("✅ [图表] 完成: %s", asset.png_path)
        generated.append(asset)

    result = FigureBuildResult(
        output_dir=str(out),
        figures_dir=str(figures_dir),
        manifest=str(manifest_path),
        generated=generated,
        failed=failed,
        renderer_version=renderer_version,
        reused_count=reused_count,
        polished_count=polished_count,
    )
    manifest_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return result


@dataclass(frozen=True)
class FigureExportResult:
    """从权威 .data/figures 收集并复制到导出目录的图表资产。"""

    figures_dir: str
    manifest: str
    assets: list[FigureAsset]
    missing: list[FigureFailure]


def collect_figure_assets_for_export(
        state: BookState,
        export_figures_dir: str | Path,
        *,
        source_figures_dir: str | Path,
        illustrations: dict[str, Any] | None = None,
) -> FigureExportResult:
    """从权威图表存储（.data/figures）读取已生成资产，复制 PNG 到导出目录。

    导出不再实时生成图；若某个 book-figure 在权威 manifest 中没有匹配资产
    （未 build 或 brief 已改导致 body_hash 不符），记入 missing 由调用方拒绝导出。
    """
    illustration_cfg = illustrations or state.style.illustrations or {}
    source_dir = Path(source_figures_dir)
    export_dir = Path(export_figures_dir)
    manifest_path = source_dir / "manifest.json"
    manifest_assets = _load_manifest_assets_for_audit(manifest_path)
    scan_result = scan_figure_specs(state, illustrations=illustration_cfg)

    assets: list[FigureAsset] = []
    missing: list[FigureFailure] = list(scan_result.failed)
    for spec in scan_result.specs:
        manifest_asset = manifest_assets.get((spec.chapter_id, spec.occurrence, spec.body_hash))
        if manifest_asset is None or not Path(manifest_asset.png_path).exists():
            missing.append(
                FigureFailure(
                    chapter_id=spec.chapter_id,
                    section_id=spec.section_id,
                    occurrence=spec.occurrence,
                    figure_id=spec.figure_id,
                    reason="权威图表存储缺少匹配资产，请先执行 `figures build`（或 brief 已改动需重新生成）",
                    body_hash=spec.body_hash,
                )
            )
            continue
        stem = Path(manifest_asset.png_path).stem
        chapter_export_dir = export_dir / f"chapter-{spec.chapter_id:02d}"
        chapter_export_dir.mkdir(parents=True, exist_ok=True)
        target_png = chapter_export_dir / f"{stem}.png"
        _copy_asset_file(Path(manifest_asset.png_path), target_png)
        markdown_path = f"figures/chapter-{spec.chapter_id:02d}/{stem}.png"
        assets.append(replace(manifest_asset, png_path=str(target_png), markdown_path=markdown_path))

    return FigureExportResult(
        figures_dir=str(export_dir),
        manifest=str(manifest_path),
        assets=assets,
        missing=missing,
    )


def replace_book_figures_with_images(
        markdown: str,
        chapter_id: int,
        assets: list[FigureAsset],
        *,
        marker: str = "book-figure",
        image_prefix: str = "",
) -> str:
    """把章节正文中的 `book-figure` 规格块替换为 PNG 图片引用。"""
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
            parts.append(f"![{asset.title}]({image_path}){{width={_PUBLICATION_IMAGE_WIDTH}}}\n\n*{asset.caption}*")
        cursor = block.end
    parts.append(markdown[cursor:])
    return "".join(parts)


def audit_figure_assets(
        state: BookState,
        output_dir: str | Path,
        *,
        illustrations: dict[str, Any] | None = None,
        project_dir: str | Path | None = None,
        figures_dir: str | Path | None = None,
) -> dict[str, object]:
    """审计最终入书图的生成状态与精品图覆盖情况。"""
    illustration_cfg = illustrations or state.style.illustrations or {}
    out = Path(output_dir)
    figures_dir = Path(figures_dir) if figures_dir is not None else out / "figures"
    manifest_path = figures_dir / "manifest.json"
    polished_dir = _resolve_polished_assets_dir(project_dir, illustration_cfg)
    min_polished_png_bytes = int(illustration_cfg.get("polished_min_png_bytes") or 0)
    require_polished = bool(illustration_cfg.get("polished_required_for_export") or False)
    scan_result = scan_figure_specs(state, illustrations=illustration_cfg)
    manifest_assets = _load_manifest_assets_for_audit(manifest_path)

    items: list[dict[str, object]] = []
    polished_count = 0
    generated_count = 0
    missing_polished_count = 0
    missing_output_count = 0
    for spec in scan_result.specs:
        manifest_asset = manifest_assets.get((spec.chapter_id, spec.occurrence, spec.body_hash))
        polished_source = _find_polished_source(spec, polished_dir)
        issues: list[str] = []
        if polished_source is None:
            issues.append("missing_polished_asset")
            missing_polished_count += 1
        else:
            polished_issue = _polished_source_issue(polished_source, min_png_bytes=min_polished_png_bytes)
            if polished_issue:
                issues.append(polished_issue)
        if manifest_asset is None or not Path(manifest_asset.png_path).exists():
            issues.append("missing_generated_output")
            missing_output_count += 1

        is_polished = polished_source is not None or (manifest_asset is not None and manifest_asset.source == "polished")
        quality_tier = "publication" if is_polished else "standard"
        if is_polished:
            polished_count += 1
        if manifest_asset is not None:
            generated_count += 1
        items.append(
            {
                "chapter_id": spec.chapter_id,
                "section_id": spec.section_id,
                "occurrence": spec.occurrence,
                "figure_id": spec.figure_id,
                "type": spec.figure_type,
                "title": spec.title,
                "quality_tier": quality_tier,
                "polished": is_polished,
                "source": manifest_asset.source if manifest_asset is not None else None,
                "png_path": manifest_asset.png_path if manifest_asset is not None else None,
                "polished_source": _polished_source_paths(polished_source),
                "issues": issues,
            }
        )

    blocking_items = [item for item in items if require_polished and _audit_item_blocks_publication(item)]
    return {
        "output_dir": str(out),
        "figures_dir": str(figures_dir),
        "manifest": str(manifest_path),
        "polished_assets_dir": str(polished_dir),
        "total": len(scan_result.specs),
        "generated": generated_count,
        "polished": polished_count,
        "standard": len(scan_result.specs) - polished_count,
        "missing_polished": missing_polished_count,
        "missing_output": missing_output_count,
        "invalid_specs": len(scan_result.failed),
        "polished_required_for_export": require_polished,
        "pass": not scan_result.failed and (not require_polished or not blocking_items),
        "blocking_count": len(blocking_items) + len(scan_result.failed),
        "blocking": blocking_items[:30],
        "invalid_spec_failures": [asdict(failure) for failure in scan_result.failed[:30]],
        "items": items,
    }


def _audit_item_blocks_publication(item: dict[str, object]) -> bool:
    if not item.get("polished"):
        return True
    issues = item.get("issues")
    return isinstance(issues, list) and any(str(issue).startswith("invalid_polished_asset") for issue in issues)


def write_figure_polish_plan(
        state: BookState,
        plan_path: str | Path,
        *,
        illustrations: dict[str, Any] | None = None,
        project_dir: str | Path | None = None,
) -> dict[str, object]:
    """生成面向外部精品制图/architecture-diagram 技能的重绘计划。"""
    illustration_cfg = illustrations or state.style.illustrations or {}
    polished_dir = _resolve_polished_assets_dir(project_dir, illustration_cfg)
    scan_result = scan_figure_specs(state, illustrations=illustration_cfg)
    items: list[dict[str, object]] = []
    for spec in scan_result.specs:
        target_dir = polished_dir / f"chapter-{spec.chapter_id:02d}"
        source = _find_polished_source(spec, polished_dir)
        items.append(
            {
                "chapter_id": spec.chapter_id,
                "section_id": spec.section_id,
                "occurrence": spec.occurrence,
                "figure_id": spec.figure_id,
                "type": spec.figure_type,
                "title": spec.title,
                "status": "ready" if source is not None else "pending",
                "priority": _polish_priority(spec),
                "target_files": {
                    "html": str(target_dir / f"{spec.figure_id}.html"),
                    "svg": str(target_dir / f"{spec.figure_id}.svg"),
                    "png": str(target_dir / f"{spec.figure_id}.png"),
                },
                "prompt": _build_polish_prompt(spec),
            }
        )
    payload: dict[str, object] = {
        "version": 1,
        "profile": "architecture-diagram-publication",
        "polished_assets_dir": str(polished_dir),
        "total": len(items),
        "ready": sum(1 for item in items if item["status"] == "ready"),
        "pending": sum(1 for item in items if item["status"] == "pending"),
        "invalid_specs": len(scan_result.failed),
        "invalid_spec_failures": [asdict(failure) for failure in scan_result.failed],
        "items": items,
    }
    path = Path(plan_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_polish_prompt_files(items, polished_dir)
    payload["plan_path"] = str(path)
    payload["prompt_dir"] = str(polished_dir / "prompts")
    return payload


def _load_manifest_assets_for_audit(manifest_path: Path) -> dict[tuple[int, int, str], FigureAsset]:
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


def _polished_source_issue(source: PolishedFigureSource, *, min_png_bytes: int) -> str:
    try:
        _load_polished_svg(source)
        if source.png_path is not None:
            _validate_png_file(source.png_path, min_bytes=min_png_bytes)
    except (OSError, RuntimeError, ValueError) as exc:
        return f"invalid_polished_asset: {exc}"
    return ""


def _polished_source_paths(source: PolishedFigureSource | None) -> dict[str, str | None]:
    if source is None:
        return {"html": None, "svg": None, "png": None}
    return {
        "html": str(source.html_path) if source.html_path is not None else None,
        "svg": str(source.svg_path) if source.svg_path is not None else None,
        "png": str(source.png_path) if source.png_path is not None else None,
    }


def _polish_priority(spec: FigureSpec) -> str:
    if spec.figure_type in {"architecture", "dataflow", "topology", "layered", "sequence"}:
        return "core"
    if spec.figure_type in {"flowchart", "lifecycle", "matrix"}:
        return "high"
    return "normal"


def _build_polish_prompt(spec: FigureSpec) -> str:
    payload = {
        "id": spec.figure_id,
        "type": spec.figure_type,
        "title": spec.title,
        "purpose": spec.purpose,
        "audience_takeaway": spec.audience_takeaway,
        "visual_focus": spec.visual_focus,
        "layout": spec.layout,
        "components": spec.components,
        "connections": spec.connections,
        "regions": spec.regions,
        "callouts": spec.callouts,
        "legend": spec.legend,
        "caption": spec.caption,
        "visual_constraints": spec.visual_constraints,
    }
    return f"""请按 architecture-diagram 技能的出版级暗色技术图风格，重绘下面这张书籍插图。

硬性要求：
1. 输出 self-contained HTML，主体为 inline SVG；同时导出同名 SVG 与 PNG。
2. 画布建议 1600×1000 或 1800×1100，暗色背景、细网格、圆角卡片、清晰箭头、图例置于边界外。
3. 节点短标签优先，解释写入 callouts；禁止“节点1/节点2/container/service/user”等占位词。
4. 每张图只表达一个主结论，主链路高亮，边界、层级、时序或决策关系必须一眼可读。
5. 中文字体使用系统无衬线或 JetBrains Mono fallback；PNG 需适合 Word 印刷，文字不得重叠或过小。
6. 保持全书统一视觉语义：蓝=核心平台，青绿=边缘/接入，橙=AI/智能，紫=数据，红=安全/风险，灰=外部依赖。

图表 brief：
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""


def _write_polish_prompt_files(items: list[dict[str, object]], polished_dir: Path) -> None:
    prompt_root = polished_dir / "prompts"
    for item in items:
        chapter_id = _object_to_int(item["chapter_id"])
        figure_id = str(item["figure_id"])
        prompt = str(item["prompt"])
        prompt_dir = prompt_root / f"chapter-{chapter_id:02d}"
        prompt_dir.mkdir(parents=True, exist_ok=True)
        (prompt_dir / f"{figure_id}.md").write_text(prompt, encoding="utf-8")


def _object_to_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"无法转换为整数: {value!r}")


def render_figure_blueprint_svg(spec: FigureSpec, *, palette: dict[str, str], blueprint: dict[str, Any]) -> str:
    """把 AI 结构化设计蓝图渲染成出版级 SVG。"""
    layout = _bp_layout(_bp_text_value(blueprint.get("layout"), spec.figure_type), spec.figure_type)
    title = _bp_text_value(blueprint.get("title"), spec.title)
    subtitle = _bp_text_value(blueprint.get("subtitle"), spec.audience_takeaway or spec.purpose)
    nodes = _bp_nodes(blueprint.get("nodes") or spec.components, spec)
    edges = _bp_edges(blueprint.get("edges") or spec.connections, nodes, spec)
    groups = _bp_groups(blueprint.get("groups") or spec.regions, nodes)
    legend = _bp_compact_items(_bp_string_list(blueprint.get("legend")) or spec.legend, limit=3, chars=54)
    brief_callouts = [item for item in [spec.visual_focus, spec.audience_takeaway] if item]
    callout_candidates = _bp_string_list(blueprint.get("callouts")) or spec.callouts or brief_callouts or spec.relationships
    callouts = _bp_compact_items([item for item in callout_candidates if item], limit=3, chars=58)

    if layout == "sequence":
        body = _bp_render_sequence(nodes, edges, palette)
    elif layout in {"flowchart", "lifecycle"}:
        body = _bp_render_flowchart(nodes, edges, palette)
    elif layout in {"layered", "pyramid"}:
        body = _bp_render_layered(nodes, palette, pyramid=layout == "pyramid")
    elif layout == "matrix":
        body = _bp_render_matrix(nodes, groups, palette)
    elif layout == "timeline":
        body = _bp_render_timeline(nodes, edges, palette)
    else:
        body = _bp_render_network(nodes, edges, groups, palette, flow=layout in {"flowchart", "lifecycle", "dataflow"})

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000" role="img" aria-labelledby="title desc">
  <title id="title">{_escape(title)}</title>
  <desc id="desc">{_escape(subtitle)}</desc>
  <defs>
    <pattern id="bp-grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M 40 0 L 0 0 0 40" fill="none" stroke="{palette['line']}" stroke-width="0.45" opacity="0.28"/></pattern>
    <marker id="bp-arrow" markerWidth="12" markerHeight="8" refX="11" refY="4" orient="auto"><polygon points="0 0, 12 4, 0 8" fill="{palette['line']}"/></marker>
    <filter id="bp-shadow" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="10" stdDeviation="10" flood-color="#0F172A" flood-opacity="0.10"/></filter>
  </defs>
  <rect width="1600" height="1000" rx="0" fill="{palette['canvas']}"/>
  <rect x="32" y="32" width="1536" height="936" rx="28" fill="url(#bp-grid)" stroke="{palette['line']}" stroke-width="1.2"/>
  <rect x="64" y="58" width="1472" height="96" rx="20" fill="{palette['panel']}" stroke="{palette['line']}" stroke-width="1" filter="url(#bp-shadow)"/>
  <rect x="64" y="58" width="10" height="96" rx="5" fill="{palette['primary']}"/>
  <text x="96" y="108" fill="{palette['text']}" font-size="34" font-family="{_FONT_FAMILY}" font-weight="800">{_escape(_short(title, 42))}</text>
  <text x="98" y="136" fill="{palette['neutral']}" font-size="16" font-family="{_FONT_FAMILY}">{_escape(_short(subtitle, 92))}</text>
  {body}
  {_bp_render_callouts(callouts, palette, visible=len(nodes) <= 6 and layout not in {'flowchart', 'lifecycle', 'layered', 'pyramid', 'timeline'})}
  {_bp_render_legend(legend, palette)}
</svg>'''


def _bp_nodes(value: object, spec: FigureSpec) -> list[dict[str, str]]:
    nodes: list[dict[str, str]] = []
    if isinstance(value, list):
        for index, item in enumerate(value[:10], start=1):
            if not isinstance(item, dict):
                continue
            raw_label = _bp_text_value(item.get("label"), "")
            source = spec.elements[index - 1] if (not raw_label or _bp_is_generic_label(raw_label)) and index <= len(spec.elements) else ""
            role_source = _bp_text_value(item.get("role"), "") or _bp_text_value(item.get("subtitle"), "")
            label, role = _bp_label_and_role(
                raw_label,
                role=role_source,
                source=source,
            )
            if not label:
                continue
            nodes.append(
                {
                    "id": _safe_slug(_bp_text_value(item.get("id"), f"n{index}")) or f"n{index}",
                    "label": label,
                    "group": _bp_clean_text(_bp_text_value(item.get("group"), ""), chars=18),
                    "role": role,
                    "emphasis": _bp_clean_text(_bp_text_value(item.get("emphasis"), "") or _bp_text_value(item.get("priority"), "normal"), chars=18),
                    "shape": _bp_clean_text(_bp_text_value(item.get("shape"), ""), chars=18) or _bp_node_shape(label, role, source),
                }
            )
    if nodes:
        return nodes
    for index, item in enumerate((spec.elements or [spec.title])[:10], start=1):
        label, role = _bp_label_and_role("", role="", source=item)
        nodes.append(
            {
                "id": f"n{index}",
                "label": label or _short(item, 34),
                "group": "",
                "role": role,
                "emphasis": "normal",
                "shape": _bp_node_shape(label, role, item),
            }
        )
    return nodes


def _bp_edges(value: object, nodes: list[dict[str, str]], spec: FigureSpec) -> list[dict[str, str]]:
    node_ids = {node["id"] for node in nodes}
    edges: list[dict[str, str]] = []
    if isinstance(value, list):
        for item in value[:10]:
            if not isinstance(item, dict):
                continue
            source = _safe_slug(_bp_text_value(item.get("from"), ""))
            target = _safe_slug(_bp_text_value(item.get("to"), ""))
            if source in node_ids and target in node_ids:
                edges.append(
                    {
                        "from": source,
                        "to": target,
                        "label": _bp_edge_label(_bp_text_value(item.get("label"), "")),
                        "style": _bp_text_value(item.get("style"), "") or _bp_text_value(item.get("direction"), "solid"),
                    }
                )
    if edges or len(nodes) < 2:
        return edges
    relationships = spec.relationships or ["主链路"] * (len(nodes) - 1)
    for index in range(min(len(nodes) - 1, 8)):
        edges.append({"from": nodes[index]["id"], "to": nodes[index + 1]["id"], "label": _bp_edge_label(relationships[index % len(relationships)]), "style": "solid"})
    return edges


def _bp_groups(value: object, nodes: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: list[dict[str, str]] = []
    if isinstance(value, list):
        for item in value[:4]:
            if not isinstance(item, dict):
                continue
            label = _bp_text_value(item.get("label"), "")
            if label:
                groups.append(
                    {
                        "id": _safe_slug(_bp_text_value(item.get("id"), label)) or f"g{len(groups) + 1}",
                        "label": _bp_clean_text(label, chars=20),
                        "role": _bp_clean_role(_bp_text_value(item.get("role"), ""), chars=24),
                    }
                )
    if groups:
        return groups
    seen: list[str] = []
    for node in nodes:
        group = node.get("group", "")
        if group and group not in seen:
            seen.append(group)
    return [{"id": _safe_slug(group) or f"g{index}", "label": group, "role": ""} for index, group in enumerate(seen[:4], start=1)]


def _bp_layout(value: str, fallback: str) -> str:
    allowed = {"architecture", "sequence", "flowchart", "dataflow", "pyramid", "layered", "topology", "lifecycle", "matrix", "timeline"}
    layout = value.strip().lower()
    if layout in allowed:
        return layout
    fallback_layout = fallback.strip().lower()
    return fallback_layout if fallback_layout in allowed else "architecture"


def _bp_label_and_role(label: str, *, role: str, source: str) -> tuple[str, str]:
    label = _bp_clean_text(label, chars=34)
    role = _bp_clean_role(role, chars=42)
    source_label, source_role = _bp_extract_label_role(source)
    if _bp_is_generic_label(label):
        if source_label and not _bp_is_generic_label(source_label):
            return source_label, source_role or role
        role_label, role_note = _bp_extract_label_role(role)
        if role_label and not _bp_is_generic_label(role_label):
            return role_label, role_note or source_role
    if not label and source_label:
        return source_label, source_role or role
    if role and _bp_is_generic_label(role):
        role = source_role
    if label and not role and source_role:
        return label, source_role
    return label, role


def _bp_extract_label_role(value: str) -> tuple[str, str]:
    text = _bp_normalize_quotes(value)
    text = re.sub(r"^[\-•\s]+", "", text).strip()
    if not text:
        return "", ""
    prefix = ""
    suffix = text
    match = re.match(r"^([^:：]{1,24})[:：]\s*(.+)$", text)
    if match:
        prefix = match.group(1).strip()
        suffix = match.group(2).strip()
    quoted = _bp_first_quoted(suffix)
    if prefix and (_bp_is_generic_label(prefix) or any(key in prefix for key in ["决策", "判断"])):
        label = quoted or _bp_first_clause(suffix)
        role = _bp_role_from_suffix(suffix, label)
        return _bp_clean_text(label, chars=34), _bp_clean_role(role, chars=42)
    if prefix:
        label = prefix
        role = _bp_role_from_suffix(suffix, quoted or "")
        return _bp_clean_text(label, chars=34), _bp_clean_role(role, chars=42)
    label = quoted or _bp_first_clause(text)
    role = _bp_role_from_suffix(text, label)
    return _bp_clean_text(label, chars=34), _bp_clean_role(role, chars=42)


def _bp_role_from_suffix(suffix: str, label: str) -> str:
    text = suffix.replace(label, "", 1).strip(" ，。；;：:—-、") if label else suffix
    for separator in ["——", "--", "—", "；", ";", "。"]:
        if separator in suffix:
            tail = suffix.split(separator, 1)[1].strip()
            if tail:
                return tail
    return text


def _bp_first_quoted(value: str) -> str:
    match = _CHINESE_QUOTE_RE.search(value)
    return match.group(1).strip() if match else ""


def _bp_first_clause(value: str) -> str:
    text = value.strip(" ，。；;：:—-")
    for separator in ["——", "--", "—", "；", ";", "。", "，"]:
        if separator in text:
            text = text.split(separator, 1)[0]
            break
    text = re.sub(r"以.+?表示$", "", text).strip()
    return text


def _bp_clean_text(value: str, *, chars: int) -> str:
    text = _bp_normalize_quotes(value)
    text = re.sub(r"\s+", " ", text).strip(" ，。；;：:、")
    text = text.replace("您的", "")
    if len(text) <= chars:
        return text
    return text[:chars - 1].rstrip(" ，。；;：:、") + "…"


def _bp_clean_role(value: str, *, chars: int) -> str:
    text = _bp_clean_text(value, chars=chars)
    text = _bp_clean_generic_references(text)
    mapped = _ASCII_ROLE_MAP.get(text.lower())
    if mapped is not None:
        return mapped
    if re.fullmatch(r"[A-Za-z0-9_\-/ ]{1,24}", text):
        return ""
    return text


def _bp_clean_generic_references(value: str) -> str:
    text = re.sub(r"(?:进入|转入|指向|到)?(?:节点|决策节点|判断节点|处理节点)\d+", "进入下一判断", value)
    text = re.sub(r"最右侧(?:路径)?", "推荐路径", text)
    text = re.sub(r"进入下一判断(?:判断)?", "进入下一判断", text)
    return text.strip(" ，。；;：:、")


def _bp_normalize_quotes(value: str) -> str:
    return str(value or "").replace("“", "‘").replace("”", "’").strip()


def _bp_is_generic_label(value: str) -> bool:
    text = _bp_clean_text(value, chars=24)
    return not text or bool(_GENERIC_NODE_LABEL_RE.fullmatch(text))


def _bp_node_shape(label: str, role: str, source: str) -> str:
    text = " ".join([label, role, source])
    if any(key in text for key in ["判断", "是否", "？", "?"]):
        return "decision"
    if any(key in text for key in ["输入", "数据源", "API", "传感器"]):
        return "data"
    if any(key in text for key in ["结束", "完成", "状态"]):
        return "terminal"
    return "process"


def _bp_edge_label(value: str) -> str:
    text = _bp_clean_text(value, chars=30)
    if "；" in text and "节点" in text:
        return ""
    if re.fullmatch(r"(?:节点|决策节点)\d+是→(?:节点|决策节点)\d+", text):
        return "是"
    if re.fullmatch(r"(?:节点|决策节点)\d+否→.+", text):
        return "否"
    text = re.sub(r"^(?:节点\d+|决策节点\d+)是→", "是 → ", text)
    text = re.sub(r"；(?:节点\d+|决策节点\d+)是→", "；是 → ", text)
    text = re.sub(r" → (?:节点|决策节点)\d+", "", text)
    return _short(text, 30)


def _bp_compact_items(items: list[str], *, limit: int, chars: int) -> list[str]:
    return [_bp_clean_text(item, chars=chars) for item in items[:limit] if _bp_clean_text(item, chars=chars)]


def _bp_render_network(
        nodes: list[dict[str, str]],
        edges: list[dict[str, str]],
        groups: list[dict[str, str]],
        palette: dict[str, str],
        *,
        flow: bool,
) -> str:
    positions = _bp_flow_positions(len(nodes)) if flow else _bp_grid_positions(len(nodes))
    by_id = {node["id"]: positions[index] for index, node in enumerate(nodes)}
    arrows: list[str] = []
    panels: list[str] = []
    cards: list[str] = []
    if groups:
        panels.extend(_bp_group_panels(groups, nodes, positions, palette))
    for edge in edges:
        if edge["from"] not in by_id or edge["to"] not in by_id:
            continue
        source_box = by_id[edge["from"]]
        target_box = by_id[edge["to"]]
        dashed = edge.get("style") in {"dashed", "async", "optional"}
        arrows.append(_bp_connector(source_box, target_box, palette, dashed=dashed))
        if edge.get("label"):
            x1, y1, w1, h1 = source_box
            x2, y2, w2, h2 = target_box
            label_x = (x1 + w1 / 2 + x2 + w2 / 2) / 2
            label_y = (y1 + h1 / 2 + y2 + h2 / 2) / 2 - 10
            arrows.extend(_text_lines(edge["label"], label_x, label_y, 170, palette["neutral"], 11, anchor="middle", max_lines=1, char_factor=1.25))
    for index, node in enumerate(nodes):
        x, y, width, height = positions[index]
        cards.append(_bp_card(x, y, width, height, node["label"], _bp_node_color(node, index, palette), palette, subtitle=node.get("role", "")))
    return "\n  ".join([*panels, *arrows, *cards])


def _bp_render_flowchart(nodes: list[dict[str, str]], edges: list[dict[str, str]], palette: dict[str, str]) -> str:
    positions = _bp_flowchart_positions(len(nodes))
    by_id = {node["id"]: positions[index] for index, node in enumerate(nodes)}
    arrows: list[str] = []
    cards: list[str] = []
    for edge in edges:
        if edge["from"] not in by_id or edge["to"] not in by_id:
            continue
        arrows.append(_bp_connector(by_id[edge["from"]], by_id[edge["to"]], palette, dashed=edge.get("style") in {"dashed", "async", "optional"}))
    for index, node in enumerate(nodes):
        x, y, width, height = positions[index]
        color = _bp_node_color(node, index, palette)
        if node.get("shape") == "decision":
            cards.append(_bp_decision_card(x, y, width, height, node["label"], color, palette, subtitle=node.get("role", "")))
        elif _bp_is_highlight_node(node):
            cards.append(_bp_highlight_card(x, y, width, height, node["label"], palette, subtitle=node.get("role", "")))
        else:
            cards.append(_bp_card(x, y, width, height, node["label"], color, palette, subtitle=node.get("role", "")))
    return "\n  ".join([*arrows, *cards])


def _bp_render_sequence(nodes: list[dict[str, str]], edges: list[dict[str, str]], palette: dict[str, str]) -> str:
    participants = nodes[:6]
    count = max(2, len(participants))
    start_x = 150
    gap = 1300 / max(1, count - 1)
    top = 210
    bottom = 730
    parts: list[str] = []
    for index, node in enumerate(participants):
        x = start_x + index * gap
        parts.append(_bp_card(x - 95, top, 190, 64, node["label"], _bp_node_color(node, index, palette), palette, subtitle=node.get("role", "")))
        parts.append(f'<line x1="{x}" y1="{top + 70}" x2="{x}" y2="{bottom}" stroke="{palette["line"]}" stroke-width="1.5" stroke-dasharray="7 7"/>')
    messages = edges or []
    for index, edge in enumerate(messages[:8]):
        source_index = next((i for i, node in enumerate(participants) if node["id"] == edge.get("from")), index % max(1, count - 1))
        target_index = next((i for i, node in enumerate(participants) if node["id"] == edge.get("to")), min(source_index + 1, count - 1))
        x1 = start_x + source_index * gap
        x2 = start_x + target_index * gap
        y = 330 + index * 46
        parts.append(_bp_arrow(x1 + 16, y, x2 - 16, y, palette, dashed=edge.get("style") in {"dashed", "async"}))
        if edge.get("label"):
            parts.extend(_text_lines(edge["label"], (x1 + x2) / 2, y - 12, abs(x2 - x1) - 40, palette["neutral"], 12, anchor="middle", max_lines=1, char_factor=1.2))
    return "\n  ".join(parts)


def _bp_render_layered(nodes: list[dict[str, str]], palette: dict[str, str], *, pyramid: bool) -> str:
    comparison_columns = _bp_layered_comparison_columns(nodes)
    if comparison_columns and not pyramid:
        return _bp_render_layered_comparison(comparison_columns, palette)
    layers = nodes[:8]
    parts: list[str] = []
    center = 800
    y = 198
    height = 68 if len(layers) <= 6 else 58
    gap = 16 if len(layers) <= 6 else 12
    for index, node in enumerate(layers):
        width = 520 + index * 90 if pyramid else 1140
        x = center - width / 2
        color = _bp_node_color(node, index, palette)
        if pyramid:
            top_width = max(260, width - 80)
            points = f"{center - top_width / 2},{y} {center + top_width / 2},{y} {x + width},{y + height} {x},{y + height}"
            parts.append(f'<polygon points="{points}" fill="{color}" stroke="{palette["line"]}" stroke-width="1.4"/>')
            parts.extend(_text_lines(node["label"], center, y + 39, width - 80, "white", 17, anchor="middle", max_lines=1, char_factor=1.1))
        else:
            parts.append(_bp_card(x, y, width, height, node["label"], color, palette, subtitle=node.get("role", "")))
        y += height + gap
    return "\n  ".join(parts)


def _bp_layered_comparison_columns(nodes: list[dict[str, str]]) -> list[tuple[str, list[tuple[dict[str, str], str]]]]:
    columns: dict[str, list[tuple[dict[str, str], str]]] = {}
    for node in nodes:
        label = node.get("label", "")
        match = re.match(r"^([^\-—]{1,8})[\-—](.+)$", label)
        if not match:
            return []
        prefix = match.group(1).strip()
        layer_label = match.group(2).strip()
        if not prefix or not layer_label:
            return []
        columns.setdefault(prefix, []).append((node, layer_label))
    if len(columns) < 2 or sum(len(items) for items in columns.values()) < 4:
        return []
    return list(columns.items())[:3]


def _bp_render_layered_comparison(columns: list[tuple[str, list[tuple[dict[str, str], str]]]], palette: dict[str, str]) -> str:
    column_count = len(columns)
    gap = 74 if column_count == 2 else 42
    width = (1260 - gap * (column_count - 1)) / column_count
    start_x = 170
    top_y = 244
    parts: list[str] = []
    max_layers = max(len(items) for _title, items in columns)
    card_height = min(74, max(54, (500 - 18 * (max_layers - 1)) / max_layers))
    for column_index, (title, items) in enumerate(columns):
        x = start_x + column_index * (width + gap)
        panel_height = max_layers * card_height + (max_layers - 1) * 18 + 78
        parts.append(f'<rect x="{x - 18}" y="{top_y - 58}" width="{width + 36}" height="{panel_height}" rx="24" fill="{palette["panel"]}" stroke="{palette["line"]}" stroke-width="1.2" opacity="0.82"/>')
        parts.extend(_text_lines(title, x + width / 2, top_y - 24, width - 60, palette["text"], 22, anchor="middle", max_lines=1, char_factor=1.2))
        for layer_index, (node, layer_label) in enumerate(items):
            y = top_y + layer_index * (card_height + 18)
            rendered_node = dict(node)
            rendered_node["label"] = layer_label
            color = _bp_node_color(rendered_node, layer_index, palette)
            parts.append(_bp_card(x, y, width, card_height, layer_label, color, palette, subtitle=""))
            if layer_index < len(items) - 1:
                arrow_x = x + width - 32
                parts.append(_bp_arrow(arrow_x, y + card_height + 6, arrow_x, y + card_height + 18, palette, dashed=False))
    return "\n  ".join(parts)


def _bp_render_matrix(nodes: list[dict[str, str]], groups: list[dict[str, str]], palette: dict[str, str]) -> str:
    items = nodes[:9]
    cols = 3
    width = 420
    height = 118
    start_x = 160
    start_y = 230
    parts: list[str] = []
    for index, node in enumerate(items):
        row = index // cols
        col = index % cols
        x = start_x + col * (width + 28)
        y = start_y + row * (height + 28)
        fill = "#FFFFFF" if (row + col) % 2 == 0 else "#EFF6FF"
        parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="18" fill="{fill}" stroke="{_bp_node_color(node, index, palette)}" stroke-width="2"/>')
        parts.extend(_text_lines(node["label"], x + 24, y + 42, width - 48, palette["text"], 17, anchor="start", max_lines=2, char_factor=1.1))
        if node.get("role"):
            parts.extend(_text_lines(node["role"], x + 24, y + 92, width - 48, palette["neutral"], 13, anchor="start", max_lines=1, char_factor=1.2))
    if groups:
        parts.extend(_text_lines("比较维度：" + " / ".join(group["label"] for group in groups[:3]), 160, 195, 1200, palette["neutral"], 16, anchor="start", max_lines=1, char_factor=1.2))
    return "\n  ".join(parts)


def _bp_render_timeline(nodes: list[dict[str, str]], edges: list[dict[str, str]], palette: dict[str, str]) -> str:
    milestones = nodes[:8]
    start_x = 150
    end_x = 1450
    y = 455
    gap = (end_x - start_x) / max(1, len(milestones) - 1)
    parts = [f'<line x1="{start_x}" y1="{y}" x2="{end_x}" y2="{y}" stroke="{palette["line"]}" stroke-width="4" marker-end="url(#bp-arrow)"/>']
    for index, node in enumerate(milestones):
        x = start_x + index * gap
        color = _bp_node_color(node, index, palette)
        parts.append(f'<circle cx="{x}" cy="{y}" r="18" fill="{color}" stroke="white" stroke-width="4"/>')
        label_y = y - 62 if index % 2 == 0 else y + 60
        parts.extend(_text_lines(node["label"], x, label_y, 190, palette["text"], 15, anchor="middle", max_lines=2, char_factor=1.15))
    if edges:
        parts.extend(_text_lines("关键关系：" + "；".join(edge.get("label", "") for edge in edges[:3] if edge.get("label")), 150, 690, 1300, palette["neutral"], 15, anchor="start", max_lines=2, char_factor=1.25))
    return "\n  ".join(parts)


def _bp_group_panels(
        groups: list[dict[str, str]],
        nodes: list[dict[str, str]],
        positions: list[tuple[float, float, float, float]],
        palette: dict[str, str],
) -> list[str]:
    parts: list[str] = []
    node_groups = [node.get("group", "") for node in nodes]
    for index, group in enumerate(groups[:4]):
        group_ids = {group["id"], group["label"]}
        member_indexes = [i for i, item in enumerate(node_groups) if item in group_ids]
        if not member_indexes:
            continue
        xs = [positions[i][0] for i in member_indexes]
        ys = [positions[i][1] for i in member_indexes]
        rights = [positions[i][0] + positions[i][2] for i in member_indexes]
        bottoms = [positions[i][1] + positions[i][3] for i in member_indexes]
        x = max(74, min(xs) - 24)
        y = max(178, min(ys) - 48)
        width = min(1450 - x, max(rights) - x + 24)
        height = min(575 - (y - 178), max(bottoms) - y + 28)
        parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="24" fill="{palette["panel"]}" stroke="{_node_color(index, palette)}" stroke-width="1.4" stroke-dasharray="8 6" opacity="0.72"/>')
        parts.extend(_text_lines(group["label"], x + 20, y + 30, width - 40, _node_color(index, palette), 14, anchor="start", max_lines=1, char_factor=1.2))
    return parts


def _bp_card(x: float, y: float, width: float, height: float, label: str, color: str, palette: dict[str, str], *, subtitle: str = "") -> str:
    compact = height <= 76
    label_size = 15 if compact else 16
    subtitle_size = 11 if compact else 12
    label_lines = 1 if compact and subtitle else 2
    subtitle_lines = 1 if compact else 2
    label_y = y + 38 if not compact else y + 36
    subtitle_y = y + height - 14 if compact else y + height - 24
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="18" fill="white" stroke="{palette["line"]}" stroke-width="1.1" filter="url(#bp-shadow)"/>',
        f'<rect x="{x}" y="{y}" width="{width}" height="10" rx="5" fill="{color}"/>',
        f'<circle cx="{x + 26}" cy="{y + 34}" r="7" fill="{color}"/>',
    ]
    parts.extend(_text_lines(label, x + 44, label_y, width - 64, palette["text"], label_size, anchor="start", max_lines=label_lines, char_factor=1.05))
    if subtitle:
        parts.extend(_text_lines(subtitle, x + 44, subtitle_y, width - 64, palette["neutral"], subtitle_size, anchor="start", max_lines=subtitle_lines, char_factor=1.25))
    return "\n  ".join(parts)


def _bp_decision_card(x: float, y: float, width: float, height: float, label: str, color: str, palette: dict[str, str], *, subtitle: str = "") -> str:
    center_x = x + width / 2
    center_y = y + height / 2
    diamond_width = width * 0.78
    diamond_height = height * 0.82
    points = " ".join(
        [
            f"{center_x},{center_y - diamond_height / 2}",
            f"{center_x + diamond_width / 2},{center_y}",
            f"{center_x},{center_y + diamond_height / 2}",
            f"{center_x - diamond_width / 2},{center_y}",
        ]
    )
    parts = [
        f'<polygon points="{points}" fill="#FFFBEB" stroke="{color}" stroke-width="2" filter="url(#bp-shadow)"/>',
        f'<circle cx="{x + 28}" cy="{y + 30}" r="7" fill="{color}"/>',
    ]
    parts.extend(_text_lines(label, center_x, y + 52, width - 86, palette["text"], 15, anchor="middle", max_lines=2, char_factor=1.12))
    if subtitle:
        parts.append(f'<rect x="{x + 28}" y="{y + height + 10}" width="{width - 56}" height="34" rx="17" fill="#FFF7ED" stroke="{palette["warning"]}" stroke-width="0.8" opacity="0.95"/>')
        parts.extend(_text_lines(subtitle, center_x, y + height + 32, width - 72, palette["neutral"], 11, anchor="middle", max_lines=1, char_factor=1.25))
    return "\n  ".join(parts)


def _bp_highlight_card(x: float, y: float, width: float, height: float, label: str, palette: dict[str, str], *, subtitle: str = "") -> str:
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="22" fill="#FFF7ED" stroke="{palette["accent"]}" stroke-width="2.4" filter="url(#bp-shadow)"/>',
        f'<rect x="{x}" y="{y}" width="{width}" height="12" rx="6" fill="{palette["accent"]}"/>',
        f'<circle cx="{x + 30}" cy="{y + 36}" r="8" fill="{palette["accent"]}"/>',
    ]
    parts.extend(_text_lines(label, x + 52, y + 42, width - 76, palette["text"], 16, anchor="start", max_lines=2, char_factor=1.06))
    if subtitle:
        parts.extend(_text_lines(subtitle, x + 52, y + height - 26, width - 76, palette["neutral"], 12, anchor="start", max_lines=2, char_factor=1.25))
    return "\n  ".join(parts)


def _bp_render_callouts(callouts: list[str], palette: dict[str, str], *, visible: bool) -> str:
    if not visible or not callouts:
        return ""
    x = 1038
    y = 646
    width = 430
    height = 128
    parts = [f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="18" fill="#FFF7ED" stroke="{palette["accent"]}" stroke-width="1.2" filter="url(#bp-shadow)"/>']
    parts.extend(_text_lines("关键说明", x + 22, y + 28, width - 44, palette["accent"], 14, anchor="start", max_lines=1, char_factor=1.1))
    for index, item in enumerate(callouts[:3]):
        parts.extend(_text_lines("• " + item, x + 22, y + 54 + index * 26, width - 44, palette["neutral"], 11, anchor="start", max_lines=1, char_factor=1.25))
    return "\n  ".join(parts)


def _bp_render_legend(legend: list[str], palette: dict[str, str]) -> str:
    items = legend[:3]
    if not items:
        return ""
    x = 86
    y = 814
    width = 1428
    height = 62 if len(items) <= 2 else 86
    parts = [f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="18" fill="{palette["panel"]}" stroke="{palette["line"]}" stroke-width="1"/>']
    colors = [palette["primary"], palette["secondary"], palette["accent"], palette["neutral"]]
    for index, item in enumerate(items):
        col = index % 2 if len(items) > 1 else 0
        row = index // 2
        item_x = x + 26 + col * 690
        item_y = y + 29 + row * 28
        parts.append(f'<circle cx="{item_x}" cy="{item_y}" r="7" fill="{colors[index % len(colors)]}"/>')
        parts.extend(_text_lines(item, item_x + 18, item_y + 5, 630, palette["neutral"], 12, anchor="start", max_lines=1, char_factor=1.22))
    return "\n  ".join(parts)


def _bp_render_caption(caption: str, palette: dict[str, str]) -> str:
    return "\n  ".join(_text_lines(caption, 90, 925, 1420, palette["neutral"], 14, anchor="start", max_lines=2, char_factor=1.25))


def _bp_arrow(x1: float, y1: float, x2: float, y2: float, palette: dict[str, str], *, dashed: bool) -> str:
    dash = ' stroke-dasharray="9 7"' if dashed else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="white" stroke-width="6" opacity="0.82"/><line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{palette["line"]}" stroke-width="2.4" marker-end="url(#bp-arrow)"{dash}/>'


def _bp_connector(source: tuple[float, float, float, float], target: tuple[float, float, float, float], palette: dict[str, str], *, dashed: bool) -> str:
    x1, y1, w1, h1 = source
    x2, y2, w2, h2 = target
    source_center = (x1 + w1 / 2, y1 + h1 / 2)
    target_center = (x2 + w2 / 2, y2 + h2 / 2)
    if abs(target_center[0] - source_center[0]) >= abs(target_center[1] - source_center[1]):
        if target_center[0] >= source_center[0]:
            start = (x1 + w1, source_center[1])
            end = (x2, target_center[1])
        else:
            start = (x1, source_center[1])
            end = (x2 + w2, target_center[1])
    elif target_center[1] >= source_center[1]:
        start = (source_center[0], y1 + h1)
        end = (target_center[0], y2)
    else:
        start = (source_center[0], y1)
        end = (target_center[0], y2 + h2)
    mid_x = (start[0] + end[0]) / 2
    if abs(start[1] - end[1]) < 8:
        path = f"M {start[0]} {start[1]} L {end[0]} {end[1]}"
    else:
        path = f"M {start[0]} {start[1]} L {mid_x} {start[1]} L {mid_x} {end[1]} L {end[0]} {end[1]}"
    dash = ' stroke-dasharray="9 7"' if dashed else ""
    return f'<path d="{path}" fill="none" stroke="white" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" opacity="0.82"/><path d="{path}" fill="none" stroke="{palette["line"]}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" marker-end="url(#bp-arrow)"{dash}/>'


def _bp_grid_positions(count: int) -> list[tuple[float, float, float, float]]:
    cols = count if count <= 3 else 2 if count == 4 else 3
    gap_x = 54 if cols == 3 else 72
    width = 370 if cols == 3 else min(430, (1240 - (cols - 1) * gap_x) / cols)
    height = 128 if count <= 4 else 106
    gap_y = 40 if count > 6 else 52
    total_width = cols * width + (cols - 1) * gap_x
    start_x = 800 - total_width / 2
    rows = math.ceil(count / cols) if cols else 1
    total_height = rows * height + (rows - 1) * gap_y
    start_y = max(205, 460 - total_height / 2)
    return [(start_x + (index % cols) * (width + gap_x), start_y + (index // cols) * (height + gap_y), width, height) for index in range(count)]


def _bp_flow_positions(count: int) -> list[tuple[float, float, float, float]]:
    cols = min(4, max(1, count)) if count > 5 else min(5, max(1, count))
    gap = 42
    width = 278 if count > 5 else min(300, (1280 - (cols - 1) * gap) / cols)
    height = 112 if count <= 5 else 104
    total_width = cols * width + (cols - 1) * gap
    start_x = 800 - total_width / 2
    positions: list[tuple[float, float, float, float]] = []
    for index in range(count):
        row = index // cols
        col = index % cols if row % 2 == 0 else cols - 1 - (index % cols)
        x = start_x + col * (width + gap)
        y = 300 + row * 156
        positions.append((x, y, width, height))
    return positions


def _bp_flowchart_positions(count: int) -> list[tuple[float, float, float, float]]:
    cols = min(4, max(1, count))
    gap = 54
    width = min(292, (1288 - (cols - 1) * gap) / cols)
    height = 122
    total_width = cols * width + (cols - 1) * gap
    start_x = 800 - total_width / 2
    positions: list[tuple[float, float, float, float]] = []
    for index in range(count):
        row = index // cols
        col = index % cols if row % 2 == 0 else cols - 1 - (index % cols)
        positions.append((start_x + col * (width + gap), 292 + row * 186, width, height))
    return positions


def _bp_node_color(node: dict[str, str], index: int, palette: dict[str, str]) -> str:
    text = " ".join([node.get("label", ""), node.get("role", ""), node.get("emphasis", "")]).lower()
    if any(key in text for key in ["ai", "agent", "智能", "推理", "决策", "自动"]):
        return palette["accent"]
    if any(key in text for key in ["区块链", "链上", "存证", "共识", "可信"]):
        return palette["primary"]
    if any(key in text for key in ["设备", "边缘", "传感", "网关", "采集"]):
        return palette["secondary"]
    if any(key in text for key in ["风险", "告警", "异常", "安全", "故障"]):
        return palette["warning"]
    return _node_color(index, palette)


def _bp_is_highlight_node(node: dict[str, str]) -> bool:
    text = " ".join([node.get("label", ""), node.get("role", ""), node.get("emphasis", "")])
    return any(key in text for key in ["推荐", "融合", "目标", "最终", "最右侧", "全栈", "AIoT+"])


def _bp_text_value(value: object, default: str) -> str:
    text = str(value or "").strip()
    return text or default


def _bp_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := str(item).strip())]


def _figure_dict_list(value: object, *, limit: int = 12) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, str]] = []
    for item in value[:limit]:
        if not isinstance(item, dict):
            continue
        normalized = {
            normalize_book_figure_scalar(key): normalize_book_figure_scalar(raw)
            for key, raw in item.items()
            if raw not in (None, "", []) and normalize_book_figure_scalar(key)
        }
        if normalized:
            items.append(normalized)
    return items


def _components_from_elements(elements: list[str]) -> list[dict[str, str]]:
    components: list[dict[str, str]] = []
    for index, item in enumerate(elements[:10], start=1):
        label, role = _bp_extract_label_role(item)
        label = label or _short(item, 30)
        component_type = _infer_component_type(" ".join([label, role, item]))
        group = _infer_component_group(" ".join([label, role, item]))
        components.append(
            {
                "id": f"c{index}",
                "label": label,
                "type": component_type,
                "subtitle": role,
                "group": group,
                "priority": "primary" if index == 1 else "normal",
                "shape": _bp_node_shape(label, role, item),
            }
        )
    return components


def _connections_from_relationships(relationships: list[str], components: list[dict[str, str]]) -> list[dict[str, str]]:
    if len(components) < 2:
        return []
    connections: list[dict[str, str]] = []
    labels = relationships or ["主链路"] * (len(components) - 1)
    for index in range(min(len(components) - 1, 10)):
        source = components[index].get("id", f"c{index + 1}")
        target = components[index + 1].get("id", f"c{index + 2}")
        label = labels[index % len(labels)]
        connections.append(
            {
                "from": source,
                "to": target,
                "label": _bp_edge_label(label) or "主链路",
                "style": "dashed" if any(key in label for key in ["异步", "可选", "事件", "虚线"]) else "solid",
                "direction": "left-to-right",
            }
        )
    return connections


def _regions_from_components(components: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: list[str] = []
    for component in components:
        group = component.get("group", "")
        if group and group not in seen:
            seen.append(group)
    return [{"id": group, "label": _region_label(group), "role": _region_role(group)} for group in seen[:4]]


def _infer_component_type(text: str) -> str:
    if any(key in text for key in ["设备", "边缘", "传感", "网关", "PLC", "采集"]):
        return "edge"
    if any(key in text for key in ["数据", "存储", "时序", "湖仓", "数据库"]):
        return "data"
    if any(key in text for key in ["AI", "Agent", "智能", "推理", "模型", "决策"]):
        return "ai"
    if any(key in text for key in ["安全", "权限", "认证", "审计", "告警", "风险"]):
        return "security"
    if any(key in text for key in ["应用", "业务", "运营", "用户", "场景"]):
        return "application"
    return "platform"


def _infer_component_group(text: str) -> str:
    component_type = _infer_component_type(text)
    return {
        "edge": "edge_domain",
        "data": "data_domain",
        "ai": "intelligence_domain",
        "security": "governance_domain",
        "application": "application_domain",
    }.get(component_type, "platform_domain")


def _region_label(group: str) -> str:
    return {
        "edge_domain": "设备与边缘域",
        "platform_domain": "平台服务域",
        "data_domain": "数据资产域",
        "intelligence_domain": "智能决策域",
        "governance_domain": "治理与安全域",
        "application_domain": "业务应用域",
    }.get(group, group)


def _region_role(group: str) -> str:
    return {
        "edge_domain": "现场异构资源边界",
        "platform_domain": "核心服务能力边界",
        "data_domain": "数据沉淀与治理边界",
        "intelligence_domain": "模型、规则与 Agent 边界",
        "governance_domain": "风险控制与责任边界",
        "application_domain": "业务价值交付边界",
    }.get(group, "语义分组边界")


def _design_level_from_type(figure_type: str) -> str:
    if figure_type in {"architecture", "topology", "layered"}:
        return "logical"
    if figure_type in {"sequence", "flowchart", "dataflow", "lifecycle", "timeline"}:
        return "implementation"
    if figure_type in {"matrix", "pyramid"}:
        return "decision"
    return "conceptual"


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
    payload, reason = parse_book_figure_payload(block.body)
    if payload is None:
        return None, reason
    missing = [field for field in required_fields if field not in payload or payload.get(field) in (None, "", [])]
    if missing:
        return None, "缺少字段: " + ", ".join(missing)

    figure_type = normalize_book_figure_scalar(payload.get("type") or "").lower()
    if figure_type not in allowed_types:
        return None, f"不支持的图表类型: {figure_type}"

    figure_id = _safe_slug(normalize_book_figure_scalar(payload.get("id") or "")) or _fallback_figure_id(chapter_id, occurrence)
    elements = book_figure_string_list(payload.get("elements"))
    relationships = book_figure_string_list(payload.get("relationships"))
    legend = book_figure_string_list(payload.get("legend"))
    components = _figure_dict_list(payload.get("components")) or _components_from_elements(elements)
    connections = _figure_dict_list(payload.get("connections")) or _connections_from_relationships(relationships, components)
    regions = _figure_dict_list(payload.get("regions")) or _figure_dict_list(payload.get("lanes")) or _regions_from_components(components)
    callouts = book_figure_string_list(payload.get("callouts")) or relationships[:3]
    visual_constraints = book_figure_string_list(payload.get("visual_constraints")) or [
        normalize_book_figure_scalar(payload.get("render_notes") or "")
    ]
    purpose = normalize_book_figure_scalar(payload.get("purpose") or "")
    caption = normalize_book_figure_scalar(payload.get("caption") or "")
    render_notes = normalize_book_figure_scalar(payload.get("render_notes") or "")
    audience_takeaway = normalize_book_figure_scalar(payload.get("audience_takeaway") or payload.get("takeaway") or purpose or caption)
    visual_focus = normalize_book_figure_scalar(payload.get("visual_focus") or payload.get("focus") or payload.get("layout") or purpose)
    return (
        FigureSpec(
            chapter_id=chapter_id,
            section_id=section_id,
            occurrence=occurrence,
            figure_id=figure_id,
            figure_type=figure_type,
            title=normalize_book_figure_scalar(payload.get("title") or figure_id),
            purpose=purpose,
            layout=normalize_book_figure_scalar(payload.get("layout") or ""),
            elements=elements,
            relationships=relationships,
            legend=legend,
            caption=caption,
            render_notes=render_notes,
            body_hash=body_hash,
            audience_takeaway=audience_takeaway,
            visual_focus=visual_focus,
            design_level=normalize_book_figure_scalar(payload.get("design_level") or _design_level_from_type(figure_type)),
            components=components,
            connections=connections,
            regions=regions,
            callouts=callouts,
            visual_constraints=[item for item in visual_constraints if item],
        ),
        "",
    )


def _write_figure_asset(
        spec: FigureSpec,
        *,
        figures_dir: Path,
        palette: dict[str, str],
        used_file_stems: set[str],
        designer: FigureDesigner | None,
) -> FigureAsset:
    chapter_dir = figures_dir / f"chapter-{spec.chapter_id:02d}"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    stem = _unique_file_stem(_safe_slug(spec.figure_id) or _fallback_figure_id(spec.chapter_id, spec.occurrence), used_file_stems)
    design_notes = ""
    ai_html = ""
    if designer is None:
        svg = render_figure_blueprint_svg(spec, palette=palette, blueprint={})
    else:
        svg, ai_html, design_notes = _design_ai_figure(spec, palette=palette, designer=designer)
    svg = _normalize_svg(svg)
    svg = _fit_svg_to_publication_canvas(svg)
    _validate_svg_document(svg)
    # AI 直出的完整 HTML 为主产物；兜底/模板路径则用模板外壳包裹 svg。
    html_doc = ai_html.strip() if ai_html.strip() else _render_html(spec, svg, palette, design_notes=design_notes)
    svg_path = chapter_dir / f"{stem}.svg"
    html_path = chapter_dir / f"{stem}.html"
    png_path = chapter_dir / f"{stem}.png"
    svg_path.write_text(svg, encoding="utf-8")
    html_path.write_text(html_doc, encoding="utf-8")
    render_svg_to_png(svg_path, png_path)
    markdown_path = f"figures/chapter-{spec.chapter_id:02d}/{stem}.png"
    source = "ai" if designer is not None and ai_html.strip() else "template"
    return FigureAsset(
        chapter_id=spec.chapter_id,
        section_id=spec.section_id,
        occurrence=spec.occurrence,
        figure_id=spec.figure_id,
        figure_type=spec.figure_type,
        title=spec.title,
        caption=spec.caption,
        svg_path=str(svg_path),
        html_path=str(html_path),
        png_path=str(png_path),
        markdown_path=markdown_path,
        body_hash=spec.body_hash,
        source=source,
        quality_tier="standard",
    )


def _write_polished_figure_asset(
        spec: FigureSpec,
        *,
        figures_dir: Path,
        used_file_stems: set[str],
        source: PolishedFigureSource,
        min_png_bytes: int,
) -> FigureAsset:
    chapter_dir = figures_dir / f"chapter-{spec.chapter_id:02d}"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    stem = _unique_file_stem(_safe_slug(spec.figure_id) or _fallback_figure_id(spec.chapter_id, spec.occurrence), used_file_stems)
    svg_path = chapter_dir / f"{stem}.svg"
    html_path = chapter_dir / f"{stem}.html"
    png_path = chapter_dir / f"{stem}.png"

    svg = _load_polished_svg(source)
    svg_path.write_text(svg, encoding="utf-8")
    if source.html_path is not None:
        _copy_asset_file(source.html_path, html_path)
    else:
        html_path.write_text(_render_html(spec, svg, _figure_palette({}), design_notes="出版级精品图资产"), encoding="utf-8")

    if source.png_path is not None:
        _validate_png_file(source.png_path, min_bytes=min_png_bytes)
        _copy_asset_file(source.png_path, png_path)
    else:
        render_svg_to_png(svg_path, png_path)

    markdown_path = f"figures/chapter-{spec.chapter_id:02d}/{stem}.png"
    return FigureAsset(
        chapter_id=spec.chapter_id,
        section_id=spec.section_id,
        occurrence=spec.occurrence,
        figure_id=spec.figure_id,
        figure_type=spec.figure_type,
        title=spec.title,
        caption=spec.caption,
        svg_path=str(svg_path),
        html_path=str(html_path),
        png_path=str(png_path),
        markdown_path=markdown_path,
        body_hash=spec.body_hash,
        source="polished",
        quality_tier="publication",
    )


def _resolve_polished_assets_dir(project_dir: str | Path | None, illustrations: dict[str, Any]) -> Path:
    raw_dir = normalize_book_figure_scalar(illustrations.get("polished_assets_dir") or "assets/figures/polished")
    path = Path(raw_dir)
    if path.is_absolute():
        return path
    base_dir = Path(project_dir) if project_dir is not None else Path.cwd()
    return base_dir / path


def _find_polished_source(spec: FigureSpec, polished_dir: Path) -> PolishedFigureSource | None:
    chapter_dir = polished_dir / f"chapter-{spec.chapter_id:02d}"
    stems = _polished_stem_candidates(spec)
    html_path = _first_existing_asset(chapter_dir, stems, ".html")
    svg_path = _first_existing_asset(chapter_dir, stems, ".svg")
    png_path = _first_existing_asset(chapter_dir, stems, ".png")
    if html_path is None and svg_path is None and png_path is None:
        return None
    return PolishedFigureSource(html_path=html_path, svg_path=svg_path, png_path=png_path)


def _missing_polished_reason(spec: FigureSpec, polished_dir: Path) -> str:
    chapter_dir = polished_dir / f"chapter-{spec.chapter_id:02d}"
    stems = ", ".join(_polished_stem_candidates(spec))
    return f"缺少出版级精品图资产: {chapter_dir}/{{{stems}}}.html|.svg|.png"


def _polished_stem_candidates(spec: FigureSpec) -> list[str]:
    candidates = [spec.figure_id, _safe_slug(spec.figure_id), _fallback_figure_id(spec.chapter_id, spec.occurrence)]
    result: list[str] = []
    for candidate in candidates:
        normalized = str(candidate).strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _first_existing_asset(chapter_dir: Path, stems: list[str], suffix: str) -> Path | None:
    for stem in stems:
        path = chapter_dir / f"{stem}{suffix}"
        if path.exists():
            return path
    return None


def _load_polished_svg(source: PolishedFigureSource) -> str:
    if source.svg_path is not None:
        svg = _normalize_svg(source.svg_path.read_text(encoding="utf-8"))
    elif source.html_path is not None:
        svg = _extract_inline_svg(source.html_path.read_text(encoding="utf-8"))
    else:
        raise RuntimeError("精品图至少需要提供 SVG，或提供包含内联 SVG 的 HTML")
    _validate_svg_document(svg)
    svg = _fit_svg_to_publication_canvas(svg)
    _validate_svg_document(svg)
    return svg


def _extract_inline_svg(html_text: str) -> str:
    match = re.search(r"<svg\b.*?</svg>", html_text, flags=re.DOTALL | re.IGNORECASE)
    if match is None:
        raise RuntimeError("精品 HTML 中未找到内联 SVG，无法生成 Word 所需 PNG")
    return _normalize_svg(match.group(0))


def _copy_asset_file(source: Path, target: Path) -> None:
    if source.resolve() == target.resolve():
        return
    shutil.copyfile(source, target)


def _validate_png_file(path: Path, *, min_bytes: int) -> None:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError(f"精品 PNG 文件头无效: {path}")
    if min_bytes > 0 and len(data) < min_bytes:
        raise RuntimeError(f"精品 PNG 文件过小: {path} ({len(data)} bytes < {min_bytes} bytes)")


def _design_ai_figure(spec: FigureSpec, *, palette: dict[str, str], designer: FigureDesigner) -> tuple[str, str, str]:
    """调用 AI 设计器，返回 (svg, html, notes)。

    html 为空串表示走了本地语义蓝图兜底，需由管线用模板外壳包裹 svg 生成 HTML。
    """
    feedback = ""
    last_error = ""
    for _ in range(3):
        try:
            design = designer.design(spec, palette=palette, feedback=feedback)
        except Exception as exc:
            raise RuntimeError(f"AI 图表设计调用失败: {exc}") from exc
        try:
            svg = _normalize_svg(design.svg)
            _validate_svg_document(svg)
            return svg, design.html, design.notes
        except RuntimeError as exc:
            last_error = str(exc)
            feedback = f"上一次图表未通过本地出版校验: {last_error}。请重新生成完整 HTML，不要解释。"
    raise RuntimeError(f"AI 图表设计未通过校验: {last_error}")


def _load_reusable_assets(manifest_path: Path, *, renderer_version: str) -> dict[tuple[int, int, str], FigureAsset]:
    if not manifest_path.exists():
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict) or payload.get("renderer_version") != renderer_version:
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
        if Path(asset.svg_path).exists() and Path(asset.html_path).exists() and Path(asset.png_path).exists():
            assets[(asset.chapter_id, asset.occurrence, asset.body_hash)] = asset
    return assets


def _normalize_svg(svg: str) -> str:
    cleaned = svg.strip()
    fence_match = re.fullmatch(r"```(?:svg|xml)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.I)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    start = cleaned.find("<svg")
    end = cleaned.rfind("</svg>")
    if start < 0 or end < 0:
        raise RuntimeError("SVG 缺少 <svg> 根节点")
    return cleaned[start:end + len("</svg>")].strip()


def _fit_svg_to_publication_canvas(svg: str) -> str:
    root = ElementTree.fromstring(svg)
    source_width, source_height = _svg_canvas_size(root)
    if source_width <= 0 or source_height <= 0:
        raise RuntimeError("SVG 画布尺寸无效")

    if (
            math.isclose(source_width, _PUBLICATION_CANVAS_WIDTH, abs_tol=0.01)
            and math.isclose(source_height, _PUBLICATION_CANVAS_HEIGHT, abs_tol=0.01)
            and root.get("viewBox")
            and root.get("width")
            and root.get("height")
    ):
        return svg

    inner = _svg_inner_markup(svg)
    title = _escape(_svg_child_text(root, "title") or "出版级插图")
    desc = _escape(_svg_child_text(root, "desc") or "统一横向画布，适配书籍正文排版。")
    available_width = _PUBLICATION_CANVAS_WIDTH - _PUBLICATION_CANVAS_PADDING * 2
    available_height = _PUBLICATION_CANVAS_HEIGHT - _PUBLICATION_CANVAS_PADDING * 2
    scale = min(available_width / source_width, available_height / source_height)
    fitted_width = source_width * scale
    fitted_height = source_height * scale
    offset_x = (_PUBLICATION_CANVAS_WIDTH - fitted_width) / 2
    offset_y = (_PUBLICATION_CANVAS_HEIGHT - fitted_height) / 2
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{_PUBLICATION_CANVAS_WIDTH}" height="{_PUBLICATION_CANVAS_HEIGHT}" viewBox="0 0 {_PUBLICATION_CANVAS_WIDTH} {_PUBLICATION_CANVAS_HEIGHT}" role="img" aria-labelledby="title desc">
  <title id="title">{title}</title>
  <desc id="desc">{desc}</desc>
  <rect width="{_PUBLICATION_CANVAS_WIDTH}" height="{_PUBLICATION_CANVAS_HEIGHT}" fill="#F8FAFC"/>
  <svg x="{offset_x:.3f}" y="{offset_y:.3f}" width="{fitted_width:.3f}" height="{fitted_height:.3f}" viewBox="0 0 {source_width:.3f} {source_height:.3f}" preserveAspectRatio="xMidYMid meet">
{inner}
  </svg>
</svg>'''


def _svg_canvas_size(root: ElementTree.Element) -> tuple[float, float]:
    view_box = root.get("viewBox") or root.get("viewbox")
    if view_box:
        values = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", view_box)]
        if len(values) == 4:
            return values[2], values[3]
    width = _svg_length(root.get("width"))
    height = _svg_length(root.get("height"))
    return width, height


def _svg_length(value: str | None) -> float:
    if not value:
        return 0.0
    match = re.match(r"\s*(\d+(?:\.\d+)?)", value)
    return float(match.group(1)) if match else 0.0


def _svg_inner_markup(svg: str) -> str:
    start = svg.find(">")
    end = svg.rfind("</svg>")
    if start < 0 or end < 0 or end <= start:
        raise RuntimeError("SVG 结构无效")
    return svg[start + 1:end].strip()


def _svg_child_text(root: ElementTree.Element, local_name: str) -> str:
    for child in root:
        if _local_name(child.tag).lower() == local_name:
            return "".join(child.itertext()).strip()
    return ""


def _validate_svg_document(svg: str) -> None:
    if len(svg) < 500:
        raise RuntimeError("SVG 内容过短，疑似占位图")
    try:
        root = ElementTree.fromstring(svg)
    except ElementTree.ParseError as exc:
        raise RuntimeError(f"SVG XML 解析失败: {exc}") from exc
    if _local_name(root.tag) != "svg":
        raise RuntimeError("SVG 根节点必须是 <svg>")
    if not (root.get("viewBox") or (root.get("width") and root.get("height"))):
        raise RuntimeError("SVG 必须包含 viewBox 或 width/height")
    for element in root.iter():
        tag = _local_name(element.tag).lower()
        if tag in _FORBIDDEN_SVG_TAGS:
            raise RuntimeError(f"SVG 包含不允许的标签: {tag}")
        for key, value in element.attrib.items():
            if key.lower().startswith("on"):
                raise RuntimeError(f"SVG 包含事件属性: {key}")
            if _FORBIDDEN_SVG_VALUE_RE.search(value) or _has_external_svg_url(value):
                raise RuntimeError(f"SVG 包含外部资源或不安全引用: {key}")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _has_external_svg_url(value: str) -> bool:
    normalized = re.sub(r"\s+", "", value).lower()
    return "url(" in normalized and "url(#" not in normalized


def render_svg_to_png(
        svg_path: Path,
        png_path: Path,
        *,
        width: int = _PUBLICATION_CANVAS_WIDTH,
        height: int = _PUBLICATION_CANVAS_HEIGHT,
        scale: int = 2,
) -> None:
    """把统一画布 SVG 渲染为固定比例 PNG，供 Markdown/Word 入书使用。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - 依赖缺失时给出可执行修复指引
        raise RuntimeError(
            "缺少 playwright，无法把 SVG 渲成 PNG。请执行 `uv sync` 后 `uv run playwright install chromium`。"
        ) from exc
    svg_text = svg_path.read_text(encoding="utf-8")
    html_doc = f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <style>
    html, body {{ margin: 0; padding: 0; background: #F8FAFC; }}
    svg {{ display: block; width: {width}px; height: {height}px; }}
  </style>
</head>
<body>{svg_text}</body>
</html>'''
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale)
                page.set_content(html_doc, wait_until="networkidle")
                page.locator("svg").first.screenshot(path=str(png_path))
            finally:
                browser.close()
    except Exception as exc:
        raise RuntimeError(f"SVG→PNG 渲染失败: {exc}") from exc
    if not png_path.exists():
        raise RuntimeError("SVG→PNG 渲染未产出文件")


def render_html_to_png(html_path: Path, png_path: Path, *, width: int = 1280, scale: int = 2) -> None:
    """用 headless chromium 把 self-contained HTML 渲成高 DPI PNG，供印刷使用。

    HTML 自带浅色背景与 CSS 卡片布局，sips 无法渲染这些，因此走 playwright 全页截图。
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - 依赖缺失时给出可执行修复指引
        raise RuntimeError(
            "缺少 playwright，无法把 HTML 渲成 PNG。请执行 `uv sync` 后 `uv run playwright install chromium`。"
        ) from exc
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": width, "height": 900}, device_scale_factor=scale)
                page.goto(html_path.resolve().as_uri())
                page.wait_for_load_state("networkidle")
                page.screenshot(path=str(png_path), full_page=True)
            finally:
                browser.close()
    except Exception as exc:
        raise RuntimeError(f"HTML→PNG 渲染失败: {exc}") from exc
    if not png_path.exists():
        raise RuntimeError("HTML→PNG 渲染未产出文件")


def _render_svg(spec: FigureSpec, palette: dict[str, str]) -> str:
    body = _render_svg_body(spec, palette)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760" role="img" aria-labelledby="title desc">
  <title id="title">{_escape(spec.title)}</title>
  <desc id="desc">{_escape(spec.purpose)}</desc>
  <defs>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="{palette['line']}" stroke-width="0.35" opacity="0.35"/>
    </pattern>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="{palette['line']}" />
    </marker>
  </defs>
  <rect width="1200" height="760" rx="24" fill="{palette['canvas']}"/>
  <rect x="24" y="24" width="1152" height="712" rx="20" fill="url(#grid)" stroke="{palette['line']}" stroke-width="1" opacity="0.95"/>
  <text x="60" y="72" fill="{palette['text']}" font-size="26" font-family="{_FONT_FAMILY}" font-weight="700">{_escape(spec.title)}</text>
  <text x="60" y="104" fill="{palette['neutral']}" font-size="14" font-family="{_FONT_FAMILY}">{_escape(spec.purpose[:95])}</text>
  {body}
  {_render_legend(spec.legend, palette)}
  {_render_caption(spec.caption, palette)}
</svg>
'''


def _render_caption(caption: str, palette: dict[str, str]) -> str:
    return "\n  ".join(
        _text_lines(caption, 60, 700, 1080, palette["neutral"], 13, anchor="start", max_lines=2, char_factor=1.2)
    )


def _render_svg_body(spec: FigureSpec, palette: dict[str, str]) -> str:
    if spec.figure_type == "sequence":
        return _render_sequence(spec, palette)
    if spec.figure_type in {"pyramid", "layered"}:
        return _render_layered(spec, palette, pyramid=spec.figure_type == "pyramid")
    if spec.figure_type == "matrix":
        return _render_matrix(spec, palette)
    if spec.figure_type in {"timeline", "flowchart", "lifecycle"}:
        return _render_linear(spec, palette)
    return _render_architecture(spec, palette)


def _render_architecture(spec: FigureSpec, palette: dict[str, str]) -> str:
    elements = spec.elements[:12] or [spec.title]
    cols = min(3, max(1, math.ceil(math.sqrt(len(elements)))))
    box_w = 300
    box_h = 76
    gap_x = 70
    gap_y = 72
    start_x = 90
    start_y = 160
    nodes: list[tuple[float, float, str, str]] = []
    for index, label in enumerate(elements):
        row = index // cols
        col = index % cols
        x = start_x + col * (box_w + gap_x)
        y = start_y + row * (box_h + gap_y)
        nodes.append((x, y, label, _node_color(index, palette)))
    arrows = []
    for index in range(len(nodes) - 1):
        x1, y1, _, _ = nodes[index]
        x2, y2, _, _ = nodes[index + 1]
        arrows.append(_arrow(x1 + box_w, y1 + box_h / 2, x2, y2 + box_h / 2, palette, dashed=False))
    boxes = [_box(x, y, box_w, box_h, label, color, palette) for x, y, label, color in nodes]
    relation_text = _render_relation_notes(spec.relationships[:4], 760, 510, palette)
    return "\n  ".join([*arrows, *boxes, relation_text])


def _render_linear(spec: FigureSpec, palette: dict[str, str]) -> str:
    elements = spec.elements[:6] or [spec.title]
    box_w = 165
    box_h = 82
    start_x = 86
    y = 260
    gap = 28
    parts = []
    for index, label in enumerate(elements):
        x = start_x + index * (box_w + gap)
        if index:
            parts.append(_arrow(x - gap + 4, y + box_h / 2, x - 8, y + box_h / 2, palette, dashed=False))
        parts.append(_box(x, y, box_w, box_h, label, _node_color(index, palette), palette, index_label=str(index + 1)))
    parts.append(_render_relation_notes(spec.relationships[:5], 105, 430, palette))
    return "\n  ".join(parts)


def _render_sequence(spec: FigureSpec, palette: dict[str, str]) -> str:
    participants = spec.elements[:5] or ["参与者A", "参与者B"]
    start_x = 120
    gap = 220
    top = 160
    bottom = 555
    parts = []
    for index, label in enumerate(participants):
        x = start_x + index * gap
        parts.append(_box(x - 70, top, 140, 52, label, _node_color(index, palette), palette))
        parts.append(f'<line x1="{x}" y1="{top + 52}" x2="{x}" y2="{bottom}" stroke="{palette["line"]}" stroke-width="1.2" stroke-dasharray="6 5"/>')
    messages = spec.relationships[:8] or ["调用 / 响应"]
    for index, message in enumerate(messages):
        left = start_x + (index % max(1, len(participants) - 1)) * gap
        right = left + gap
        y = 245 + index * 38
        parts.append(_arrow(left + 20, y, right - 20, y, palette, dashed=index % 2 == 1))
        parts.append(f'<text x="{(left + right) / 2}" y="{y - 8}" fill="{palette["neutral"]}" font-size="12" font-family="{_FONT_FAMILY}" text-anchor="middle">{_escape(_short(message, 38))}</text>')
    return "\n  ".join(parts)


def _render_layered(spec: FigureSpec, palette: dict[str, str], *, pyramid: bool) -> str:
    elements = spec.elements[:7] or [spec.title]
    parts = []
    center = 600
    y = 160
    height = 58
    for index, label in enumerate(elements):
        width = 260 + index * 95 if pyramid else 860
        x = center - width / 2
        color = _node_color(index, palette)
        if pyramid:
            top_w = max(width - 70, 160)
            points = f"{center - top_w / 2},{y} {center + top_w / 2},{y} {x + width},{y + height} {x},{y + height}"
            parts.append(f'<polygon points="{points}" fill="{color}" stroke="{palette["primary"]}" stroke-width="1.5" opacity="0.92"/>')
            parts.append(f'<text x="{center}" y="{y + 36}" fill="white" font-size="14" font-family="{_FONT_FAMILY}" font-weight="700" text-anchor="middle">{_escape(_short(label, 48))}</text>')
        else:
            parts.append(_box(x, y, width, height, label, color, palette))
        y += height + 18
    return "\n  ".join(parts)


def _render_matrix(spec: FigureSpec, palette: dict[str, str]) -> str:
    elements = spec.elements[:9] or [spec.title]
    cols = 3
    cell_w = 300
    cell_h = 88
    start_x = 150
    start_y = 170
    parts = []
    for index, label in enumerate(elements):
        row = index // cols
        col = index % cols
        x = start_x + col * cell_w
        y = start_y + row * cell_h
        fill = palette["panel"] if (row + col) % 2 == 0 else "#EEF2FF"
        parts.append(f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" fill="{fill}" stroke="{palette["line"]}" stroke-width="1"/>')
        parts.extend(_text_lines(label, x + 18, y + 32, cell_w - 36, palette["text"], 13, anchor="start"))
    rows = math.ceil(len(elements) / cols)
    parts.append(f'<rect x="{start_x}" y="{start_y}" width="{cell_w * cols}" height="{cell_h * rows}" fill="none" stroke="{palette["primary"]}" stroke-width="2"/>')
    return "\n  ".join(parts)


def _box(
        x: float,
        y: float,
        width: float,
        height: float,
        label: str,
        color: str,
        palette: dict[str, str],
        *,
        index_label: str = "",
) -> str:
    badge = ""
    if index_label:
        badge = f'<circle cx="{x + 22}" cy="{y + 24}" r="13" fill="{palette["panel"]}" stroke="{palette["line"]}"/><text x="{x + 22}" y="{y + 29}" fill="{palette["primary"]}" font-size="12" font-family="{_FONT_FAMILY}" font-weight="700" text-anchor="middle">{index_label}</text>'
    text_x = x + width / 2 if not index_label else x + 45
    anchor = "middle" if not index_label else "start"
    text_width = width - 34 if not index_label else width - 64
    lines = _text_lines(label, text_x, y + 30, text_width, "white", 13, anchor=anchor, max_lines=2)
    return "\n  ".join(
        [
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="14" fill="{color}" stroke="{palette["line"]}" stroke-width="1.2"/>',
            badge,
            *lines,
        ]
    )


def _arrow(x1: float, y1: float, x2: float, y2: float, palette: dict[str, str], *, dashed: bool) -> str:
    dash = ' stroke-dasharray="8 6"' if dashed else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{palette["line"]}" stroke-width="2" marker-end="url(#arrowhead)"{dash}/>'


def _render_relation_notes(items: list[str], x: float, y: float, palette: dict[str, str]) -> str:
    if not items:
        return ""
    width = 360
    height = 36 + len(items) * 26
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="12" fill="{palette["panel"]}" stroke="{palette["line"]}" stroke-width="1"/>',
        f'<text x="{x + 18}" y="{y + 28}" fill="{palette["text"]}" font-size="13" font-family="{_FONT_FAMILY}" font-weight="700">关键关系</text>',
    ]
    for index, item in enumerate(items):
        parts.append(f'<text x="{x + 18}" y="{y + 56 + index * 24}" fill="{palette["neutral"]}" font-size="12" font-family="{_FONT_FAMILY}">• {_escape(_short(item, 44))}</text>')
    return "\n  ".join(parts)


def _render_legend(legend: list[str], palette: dict[str, str]) -> str:
    items = legend[:4]
    if not items:
        return ""
    x = 60
    y = 612
    parts = [f'<rect x="{x}" y="{y}" width="1060" height="66" rx="14" fill="{palette["panel"]}" stroke="{palette["line"]}" stroke-width="1"/>']
    colors = [palette["primary"], palette["secondary"], palette["accent"], palette["neutral"]]
    for index, item in enumerate(items):
        col = index % 2
        row = index // 2
        item_x = x + 24 + col * 520
        item_y = y + 25 + row * 28
        parts.append(f'<circle cx="{item_x}" cy="{item_y}" r="6" fill="{colors[index % len(colors)]}"/>')
        parts.append(f'<text x="{item_x + 14}" y="{item_y + 5}" fill="{palette["neutral"]}" font-size="12" font-family="{_FONT_FAMILY}">{_escape(_short(item, 42))}</text>')
    return "\n  ".join(parts)


def _render_html(spec: FigureSpec, svg: str, palette: dict[str, str], *, design_notes: str = "") -> str:
    notes = design_notes or spec.render_notes
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(spec.title)}</title>
  <style>
    body {{ margin: 0; background: {palette['canvas']}; color: {palette['text']}; font-family: Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif; }}
    .page {{ max-width: 1220px; margin: 24px auto; padding: 0 20px 28px; }}
    .meta {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 12px; }}
    .card {{ background: {palette['panel']}; border: 1px solid {palette['line']}; border-radius: 14px; padding: 14px 16px; }}
    .label {{ color: {palette['neutral']}; font-size: 12px; margin-bottom: 6px; }}
    .value {{ font-size: 14px; line-height: 1.55; }}
  </style>
</head>
<body>
  <main class="page">
    {svg}
    <section class="meta">
      <div class="card"><div class="label">图表类型</div><div class="value">{_escape(spec.figure_type)}</div></div>
      <div class="card"><div class="label">布局说明</div><div class="value">{_escape(spec.layout)}</div></div>
      <div class="card"><div class="label">渲染说明</div><div class="value">{_escape(notes)}</div></div>
    </section>
  </main>
</body>
</html>
'''


def _text_lines(
        text: str,
        x: float,
        y: float,
        width: float,
        fill: str,
        font_size: int,
        *,
        anchor: str,
        max_lines: int = 3,
        char_factor: float = 0.9,
) -> list[str]:
    approx_chars = max(6, int(width / (font_size * char_factor)))
    wrapped = _wrap_text(text, approx_chars)
    lines = wrapped[:max_lines]
    if len(wrapped) > max_lines and lines:
        lines[-1] = lines[-1].rstrip("，。；、 ") + "…"
    return [
        f'<text x="{x}" y="{y + index * (font_size + 5)}" fill="{fill}" font-size="{font_size}" font-family="{_FONT_FAMILY}" font-weight="600" text-anchor="{anchor}">{_escape(line)}</text>'
        for index, line in enumerate(lines)
    ]


def _wrap_text(text: str, limit: int) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return [cleaned]
    lines = []
    cursor = 0
    while cursor < len(cleaned):
        lines.append(cleaned[cursor:cursor + limit])
        cursor += limit
    return lines


def _section_id_for_offset(markdown: str, offset: int, chapter_id: int) -> str:
    pattern = re.compile(rf"^#{{2,6}}\s+({chapter_id}\.\d+\.\d+)\b", re.MULTILINE)
    section_id = ""
    for match in pattern.finditer(markdown[:offset]):
        section_id = match.group(1)
    return section_id


def _figure_palette(illustrations: dict[str, Any]) -> dict[str, str]:
    palette = dict(_DEFAULT_PALETTE)
    raw = illustrations.get("palette")
    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(key, str) and isinstance(value, str) and value.startswith("#"):
                palette[key] = value
    return palette


def _node_color(index: int, palette: dict[str, str]) -> str:
    colors = [palette["primary"], palette["secondary"], palette["accent"], palette["neutral"], palette["success"], palette["warning"]]
    return colors[index % len(colors)]


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _fallback_figure_id(chapter_id: int, occurrence: int) -> str:
    return f"fig-{chapter_id:02d}-{occurrence:02d}"


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-._")
    return slug.lower()


def _unique_file_stem(stem: str, used: set[str]) -> str:
    candidate = stem
    suffix = 2
    while candidate in used:
        candidate = f"{stem}-{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _short(value: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned if len(cleaned) <= limit else cleaned[:limit - 1].rstrip() + "…"
