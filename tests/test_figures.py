from __future__ import annotations

from pathlib import Path

import pytest

from agents.figure_designer import FigureDesignerAgent, _fallback_blueprint, _normalize_html, _normalize_svg_body
from core.figures import (
    FigureDesign,
    FigureSpec,
    audit_figure_assets,
    build_figure_assets,
    render_figure_blueprint_svg,
    render_figure_skill_svg,
    replace_book_figures_with_images,
    write_figure_polish_plan,
)
from core.state import BookState, ChapterContent, ChapterPlan, PartPlan, StyleConfig

_FIGURE_BLOCK = '''```book-figure
id: "fig-01-01"
type: "architecture"
title: "图1-1 平台架构"
purpose: "说明设备、平台和应用之间的关系。"
layout: "自下而上分层。"
elements:
  - "设备层：传感器与网关"
  - "平台层：设备管理与数据处理"
  - "应用层：业务系统"
relationships:
  - "设备层接入平台层"
  - "平台层服务应用层"
legend:
  - "蓝色=平台服务"
  - "青绿色=设备接入"
caption: "图1-1 展示平台分层架构。"
render_notes: "HTML/SVG 渲染，统一配色。"
```'''


def _figure_state() -> BookState:
    return BookState(
        parts=[
            PartPlan(
                name="基础篇",
                prefix="一",
                chapters=[
                    ChapterPlan(
                        id=1,
                        title="概述",
                        sections=[],
                    )
                ],
            )
        ],
        style=StyleConfig(
            illustrations={
                "marker": "book-figure",
                "allowed_types": ["architecture"],
                "required_fields": [
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
                ],
            }
        ),
        chapters=[
            ChapterContent(
                chapter_id=1,
                title="概述",
                markdown=f"# 第1章 概述\n\n### 1.1.1 架构\n\n{_FIGURE_BLOCK}",
            )
        ],
    )


def _publication_svg(label: str = "出版级精修图") -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">
<title>{label}</title><desc>出版级精品图，用于验证导入流程。</desc>
<defs><marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill="#94a3b8"/></marker></defs>
<rect x="0" y="0" width="1600" height="1000" fill="#020617"/>
<rect x="80" y="80" width="1440" height="840" rx="28" fill="#0f172a" stroke="#334155" stroke-width="2"/>
<text x="120" y="150" fill="#e2e8f0" font-size="44" font-family="Arial" font-weight="700">{label}</text>
<rect x="160" y="300" width="300" height="140" rx="18" fill="#083344" stroke="#22d3ee" stroke-width="3"/>
<rect x="650" y="300" width="300" height="140" rx="18" fill="#064e3b" stroke="#34d399" stroke-width="3"/>
<rect x="1140" y="300" width="300" height="140" rx="18" fill="#78350f" stroke="#fbbf24" stroke-width="3"/>
<path d="M460 370 C540 370 570 370 650 370" fill="none" stroke="#94a3b8" stroke-width="4" marker-end="url(#arrowhead)"/>
<path d="M950 370 C1030 370 1060 370 1140 370" fill="none" stroke="#94a3b8" stroke-width="4" marker-end="url(#arrowhead)"/>
<text x="310" y="375" fill="#e0f2fe" font-size="30" text-anchor="middle">设备接入</text>
<text x="800" y="375" fill="#dcfce7" font-size="30" text-anchor="middle">平台治理</text>
<text x="1290" y="375" fill="#fef3c7" font-size="30" text-anchor="middle">智能应用</text>
<text x="160" y="560" fill="#cbd5e1" font-size="24">主链路清晰、边界明确、适合出版物插图归档。</text>
</svg>'''


def test_normalize_html_accepts_raw_svg_response() -> None:
    normalized = _normalize_html(_publication_svg("原始 SVG"))

    assert normalized.startswith("<!doctype html>")
    assert "原始 SVG" in normalized


def test_normalize_svg_body_rejects_embedded_defs() -> None:
    body = '<g data-layout="architecture"><defs><marker id="custom"/></defs>' + '<rect x="100" y="140" width="200" height="80"/>' * 20 + "</g>"

    with pytest.raises(RuntimeError, match="不允许的 SVG 标签"):
        _normalize_svg_body(body)


def _write_polished_assets(project_dir: Path, *, include_png: bool = True) -> None:
    chapter_dir = project_dir / "assets" / "figures" / "polished" / "chapter-01"
    chapter_dir.mkdir(parents=True)
    svg = _publication_svg()
    (chapter_dir / "fig-01-01.svg").write_text(svg, encoding="utf-8")
    (chapter_dir / "fig-01-01.html").write_text(f"<!doctype html><html><body>{svg}</body></html>", encoding="utf-8")
    if include_png:
        (chapter_dir / "fig-01-01.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 5000)


def test_build_figure_assets_generates_html_svg_png_and_manifest(tmp_path: Path, monkeypatch) -> None:
    calls: list[Path] = []

    def fake_render(svg_path: Path, png_path: Path, *, width: int = 1200, height: int = 760, scale: int = 2) -> None:
        calls.append(svg_path)
        assert Path(svg_path).exists()
        Path(png_path).write_bytes(b"\x89PNG\r\n\x1a\n" + b"png-data")

    monkeypatch.setattr("core.figures.render_svg_to_png", fake_render)

    result = build_figure_assets(_figure_state(), tmp_path)

    assert result.failed == []
    assert len(result.generated) == 1
    asset = result.generated[0]
    assert asset.markdown_path == "figures/chapter-01/fig-01-01.png"
    assert Path(asset.html_path).exists()
    assert Path(asset.svg_path).exists()
    assert Path(asset.png_path).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert Path(result.manifest).exists()
    assert calls and calls[0] == Path(asset.svg_path)


def test_build_figure_assets_prefers_polished_assets(tmp_path: Path, monkeypatch) -> None:
    _write_polished_assets(tmp_path)

    def fail_render(svg_path: Path, png_path: Path, *, width: int = 1200, height: int = 760, scale: int = 2) -> None:
        raise AssertionError(f"精品 PNG 已存在，不应调用本地渲染器: {svg_path}")

    monkeypatch.setattr("core.figures.render_svg_to_png", fail_render)

    result = build_figure_assets(_figure_state(), tmp_path / "output", project_dir=tmp_path, force=True)

    assert result.failed == []
    assert result.polished_count == 1
    asset = result.generated[0]
    assert asset.source == "polished"
    assert asset.quality_tier == "publication"
    assert "出版级精修图" in Path(asset.svg_path).read_text(encoding="utf-8")
    assert Path(asset.png_path).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_build_figure_assets_requires_polished_when_enabled(tmp_path: Path) -> None:
    result = build_figure_assets(_figure_state(), tmp_path / "output", project_dir=tmp_path, require_polished=True)

    assert result.generated == []
    assert len(result.failed) == 1
    assert "缺少出版级精品图资产" in result.failed[0].reason


def test_audit_figure_assets_reports_polished_gap(tmp_path: Path) -> None:
    state = _figure_state()
    state.style.illustrations["polished_required_for_export"] = True

    result = audit_figure_assets(state, tmp_path / "output", project_dir=tmp_path)

    assert result["pass"] is False
    assert result["missing_polished"] == 1
    assert result["blocking_count"] == 1


def test_write_figure_polish_plan_writes_prompts(tmp_path: Path) -> None:
    result = write_figure_polish_plan(_figure_state(), tmp_path / "assets" / "figures" / "polished" / "polish-plan.json", project_dir=tmp_path)

    assert result["total"] == 1
    assert result["pending"] == 1
    prompt_file = tmp_path / "assets" / "figures" / "polished" / "prompts" / "chapter-01" / "fig-01-01.md"
    assert prompt_file.exists()
    assert "architecture-diagram" in prompt_file.read_text(encoding="utf-8")


def test_write_figure_polish_plan_avoids_duplicate_asset_paths(tmp_path: Path) -> None:
    state = _figure_state()
    state.chapters[0].markdown = f"# 第1章 概述\n\n### 1.1.1 架构\n\n{_FIGURE_BLOCK}\n\n### 1.1.2 架构\n\n{_FIGURE_BLOCK}"

    result = write_figure_polish_plan(
        state,
        tmp_path / "assets" / "figures" / "polished" / "polish-plan.json",
        project_dir=tmp_path,
    )

    assert result["total"] == 2
    items = result["items"]
    assert isinstance(items, list)
    target_paths = [str(item["target_files"]["svg"]) for item in items]
    assert target_paths == [
        str(tmp_path / "assets/figures/polished/chapter-01/fig-01-01--occ-01.svg"),
        str(tmp_path / "assets/figures/polished/chapter-01/fig-01-01--occ-02.svg"),
    ]
    assert all(Path(path).exists() for path in [
        tmp_path / "assets/figures/polished/prompts/chapter-01/fig-01-01--occ-01.md",
        tmp_path / "assets/figures/polished/prompts/chapter-01/fig-01-01--occ-02.md",
    ])
    for target_path in target_paths:
        Path(target_path).parent.mkdir(parents=True, exist_ok=True)
        Path(target_path).write_text(_publication_svg(), encoding="utf-8")

    refreshed = write_figure_polish_plan(
        state,
        tmp_path / "assets" / "figures" / "polished" / "polish-plan.json",
        project_dir=tmp_path,
    )

    assert refreshed["ready"] == 2
    assert [str(item["target_files"]["svg"]) for item in refreshed["items"]] == target_paths


def test_write_figure_polish_plan_does_not_reuse_another_explicit_figure_id(tmp_path: Path) -> None:
    state = _figure_state()
    custom_block = _FIGURE_BLOCK.replace('id: "fig-01-01"', 'id: "custom-figure"').replace("图1-1 平台架构", "自定义图")
    state.chapters[0].markdown = f"# 第1章 概述\n\n### 1.1.1 自定义图\n\n{custom_block}\n\n### 1.1.2 显式编号图\n\n{_FIGURE_BLOCK}"
    chapter_dir = tmp_path / "assets" / "figures" / "polished" / "chapter-01"
    chapter_dir.mkdir(parents=True)
    chapter_dir.joinpath("fig-01-01.svg").write_text(_publication_svg("显式编号图"), encoding="utf-8")

    result = write_figure_polish_plan(
        state,
        tmp_path / "assets" / "figures" / "polished" / "polish-plan.json",
        project_dir=tmp_path,
    )

    items = result["items"]
    assert isinstance(items, list)
    assert [item["status"] for item in items] == ["pending", "ready"]
    assert items[0]["asset_stem"] == "custom-figure"
    assert items[1]["asset_stem"] == "fig-01-01"


def test_build_figure_assets_prefers_occurrence_specific_polished_asset(tmp_path: Path, monkeypatch) -> None:
    state = _figure_state()
    state.chapters[0].markdown = f"# 第1章 概述\n\n### 1.1.1 架构\n\n{_FIGURE_BLOCK}\n\n### 1.1.2 架构\n\n{_FIGURE_BLOCK}"
    _write_polished_assets(tmp_path)
    chapter_dir = tmp_path / "assets" / "figures" / "polished" / "chapter-01"
    chapter_dir.joinpath("fig-01-01--occ-02.svg").write_text(_publication_svg("occurrence 2"), encoding="utf-8")

    def fake_render(svg_path: Path, png_path: Path, *, width: int = 1200, height: int = 760, scale: int = 2) -> None:
        Path(png_path).write_bytes(b"\x89PNG\r\n\x1a\n" + b"png-data")

    monkeypatch.setattr("core.figures.render_svg_to_png", fake_render)
    result = build_figure_assets(state, tmp_path / "output", project_dir=tmp_path, force=True)

    assert result.polished_count == 2
    second = next(asset for asset in result.generated if asset.occurrence == 2)
    assert "occurrence 2" in Path(second.svg_path).read_text(encoding="utf-8")


def test_replace_book_figures_with_images_uses_png_path(tmp_path: Path, monkeypatch) -> None:
    def fake_render(svg_path: Path, png_path: Path, *, width: int = 1200, height: int = 760, scale: int = 2) -> None:
        Path(png_path).write_bytes(b"\x89PNG\r\n\x1a\n" + b"png-data")

    monkeypatch.setattr("core.figures.render_svg_to_png", fake_render)
    result = build_figure_assets(_figure_state(), tmp_path)
    markdown = _figure_state().chapters[0].markdown

    replaced = replace_book_figures_with_images(markdown, 1, result.generated, image_prefix="../")

    assert "```book-figure" not in replaced
    assert "![图1-1 平台架构](../figures/chapter-01/fig-01-01.png){width=15cm}" in replaced
    assert "*图1-1 展示平台分层架构。*" in replaced


def test_build_figure_assets_uses_ai_designer_when_configured(tmp_path: Path, monkeypatch) -> None:
    class FakeDesigner:
        def __init__(self) -> None:
            self.calls: list[FigureSpec] = []

        def design(self, spec: FigureSpec, *, palette: dict[str, str], feedback: str = "") -> FigureDesign:
            self.calls.append(spec)
            svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">
<title>AI 图表</title><rect x="0" y="0" width="1600" height="1000" fill="#F8FAFC"/>
<rect x="100" y="100" width="1400" height="800" rx="24" fill="#FFFFFF" stroke="#94A3B8"/>
<text x="160" y="180" fill="#0F172A" font-size="44">AI 图表设计</text>
<text x="160" y="260" fill="#475569" font-size="28">出版级 SVG，不使用模板渲染。</text>
<rect x="160" y="340" width="360" height="160" rx="18" fill="#2563EB"/>
<rect x="620" y="340" width="360" height="160" rx="18" fill="#0F766E"/>
<rect x="1080" y="340" width="360" height="160" rx="18" fill="#F97316"/>
<line x1="520" y1="420" x2="620" y2="420" stroke="#94A3B8" stroke-width="8"/>
<line x1="980" y1="420" x2="1080" y2="420" stroke="#94A3B8" stroke-width="8"/>
<text x="340" y="430" fill="#FFFFFF" font-size="30" text-anchor="middle">设备接入</text>
<text x="800" y="430" fill="#FFFFFF" font-size="30" text-anchor="middle">平台服务</text>
<text x="1260" y="430" fill="#FFFFFF" font-size="30" text-anchor="middle">业务应用</text>
</svg>'''
            html = f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"></head><body>{svg}</body></html>'
            return FigureDesign(svg=svg, html=html, notes="AI 直出浅色 HTML")

    def fake_render(svg_path: Path, png_path: Path, *, width: int = 1200, height: int = 760, scale: int = 2) -> None:
        Path(png_path).write_bytes(b"\x89PNG\r\n\x1a\n" + b"png-data")

    state = _figure_state()
    state.style.illustrations["renderer"] = "ai-html-svg"
    designer = FakeDesigner()
    monkeypatch.setattr("core.figures.render_svg_to_png", fake_render)

    result = build_figure_assets(state, tmp_path, designer=designer)

    assert result.renderer_version == "ai-html-svg-v2"
    assert result.failed == []
    assert len(designer.calls) == 1
    svg_text = Path(result.generated[0].svg_path).read_text(encoding="utf-8")
    assert "AI 图表设计" in svg_text
    assert 'width="1200" height="760" viewBox="0 0 1200 760"' in svg_text
    # AI 直出的完整 HTML 应作为 html 产物落地
    assert "<!doctype html>" in Path(result.generated[0].html_path).read_text(encoding="utf-8")


def test_blueprint_renderer_repairs_generic_flowchart_labels() -> None:
    spec = FigureSpec(
        chapter_id=13,
        section_id="13.4.4",
        occurrence=1,
        figure_id="fig-13-8",
        figure_type="flowchart",
        title="图13-8 AIoT+区块链融合的工程判断框架",
        purpose="帮助架构师判断融合投入优先级。",
        layout="三个判断节点，每个节点引出分支决策。",
        elements=[
            "节点1：‘您的数据是否需要跨组织共享？’——是/否分支。否→只需要物联网平台+本地数据库；是→进入节点2。",
            "节点2：‘共享的数据是否需要防篡改存证？’——是/否分支。否→传统云服务共享；是→引入区块链层。",
            "最右侧：标记‘AIoT+区块链’融合推荐路径，使用橙色渐变背景。",
        ],
        relationships=["节点1是→节点2；节点2是→最右侧路径。"],
        legend=["蓝色=物联网基础设施层；橙色=AI智能决策层。"],
        caption="图13-8 通过判断节点确定融合深度。",
        render_notes="标准流程图布局。",
        body_hash="hash",
    )
    blueprint = {
        "layout": "flowchart",
        "nodes": [
            {"id": "n1", "label": "节点1", "role": "container"},
            {"id": "n2", "label": "节点2", "role": "service"},
            {"id": "n3", "label": "最右侧", "role": "user"},
        ],
        "edges": [{"from": "n1", "to": "n2", "label": "节点1是→节点2", "style": "solid"}],
    }

    svg = render_figure_blueprint_svg(spec, palette=spec_palette(), blueprint=blueprint)

    assert "数据是否需要跨组织共享" in svg
    assert "防篡改" in svg
    assert "存证" in svg
    assert "AIoT+区块链" in svg
    assert ">节点1<" not in svg
    assert "节点2" not in svg
    assert "container" not in svg


def test_blueprint_renderer_uses_structured_figure_brief() -> None:
    spec = FigureSpec(
        chapter_id=2,
        section_id="2.1.1",
        occurrence=1,
        figure_id="fig-02-01",
        figure_type="architecture",
        title="图2-1 AIoT 平台分层架构",
        purpose="说明平台边界。",
        layout="分层架构。",
        elements=[],
        relationships=[],
        legend=["蓝色=平台；橙色=智能。"],
        caption="图2-1 展示设备、平台和智能层的责任边界。",
        render_notes="HTML/SVG 统一绘制。",
        body_hash="hash",
        audience_takeaway="读者应理解平台不是单一服务，而是责任边界。",
        visual_focus="设备接入到 Agent 编排的主链路。",
        design_level="logical",
        regions=[{"id": "edge_domain", "label": "设备与边缘域", "role": "现场异构资源边界"}],
        components=[
            {"id": "device_edge", "label": "设备与边缘", "type": "edge", "subtitle": "传感器、PLC、网关", "group": "edge_domain", "priority": "normal", "shape": "card"},
            {"id": "agent_orchestration", "label": "Agent 编排", "type": "ai", "subtitle": "规则、模型、工具调用", "group": "intelligence_domain", "priority": "primary", "shape": "card"},
        ],
        connections=[{"from": "device_edge", "to": "agent_orchestration", "label": "上下文供给", "style": "dashed", "direction": "event"}],
        callouts=["智能层不能绕过平台治理直接控制现场设备。"],
        visual_constraints=["最多 6 个主节点。"],
    )

    svg = render_figure_blueprint_svg(spec, palette=spec_palette(), blueprint={})

    assert "设备与边缘" in svg
    assert "Agent 编排" in svg
    assert "上下文供给" in svg
    assert "设备与边缘域" in svg
    assert "平台不是单一服务" in svg


def test_blueprint_fallback_keeps_all_elements_when_components_are_incomplete() -> None:
    spec = FigureSpec(
        chapter_id=1,
        section_id="1.1.1",
        occurrence=1,
        figure_id="fig-01-04",
        figure_type="topology",
        title="图1-4 设备连接拓扑",
        purpose="展示端到云的主链路。",
        layout="从左到右拓扑。",
        elements=["感知层", "网络层", "平台层", "应用层"],
        relationships=["上行数据", "平台处理", "应用告警"],
        legend=[],
        caption="端到云链路。",
        render_notes="统一绘制。",
        body_hash="hash",
        components=[{"id": "sensor", "label": "感知层", "type": "edge"}],
    )

    svg = render_figure_blueprint_svg(spec, palette=spec_palette(), blueprint=_fallback_blueprint(spec))

    assert all(label in svg for label in spec.elements)


def test_blueprint_renderer_uses_architecture_skill_publication_style() -> None:
    spec = FigureSpec(
        chapter_id=1,
        section_id="1.1.1",
        occurrence=1,
        figure_id="fig-01-04",
        figure_type="architecture",
        title="图1-4 智慧工厂设备连接拓扑",
        purpose="展示设备、边缘、平台和应用的主链路。",
        layout="从左到右分层。",
        elements=["设备层", "边缘网关", "云平台", "业务应用"],
        relationships=["采集", "上报", "告警"],
        legend=["蓝色=主链路", "青绿=设备与边缘"],
        caption="图1-4 展示从现场设备到业务应用的端到端链路。",
        render_notes="architecture-diagram 浅色出版样式。",
        body_hash="hash",
    )

    svg = render_figure_blueprint_svg(spec, palette=spec_palette(), blueprint=_fallback_blueprint(spec))

    assert 'width="1800" height="900" viewBox="0 0 1800 900"' in svg
    assert 'data-style="architecture-diagram-wireframe-white"' in svg
    assert ">ARCHITECTURE<" in svg
    assert spec.caption in svg
    assert "bp-shadow" not in svg
    assert 'fill="#FFFFFF"' in svg


def test_skill_renderer_replaces_incomplete_subtitle_with_complete_purpose() -> None:
    spec = FigureSpec(
        chapter_id=7,
        section_id="7.5.3",
        occurrence=1,
        figure_id="fig-7-5-3-1",
        figure_type="architecture",
        title="IoT DC3 Agentic Center 的 Copilot 到 Agent 三阶段演进路线",
        purpose="展示从 Copilot 到 Agent 的三阶段演进路径。",
        layout="水平时间轴。",
        elements=[],
        relationships=[],
        legend=[],
        caption="三阶段演进路线。",
        render_notes="浅色出版样式。",
        body_hash="hash",
        audience_takeaway="读者应理解 Copilo…中的主链路。",
    )

    svg = render_figure_skill_svg(
        spec,
        palette=spec_palette(),
        body_svg='<g data-layout="architecture"><rect x="200" y="200" width="800" height="300"/></g>',
    )

    assert spec.purpose in svg
    assert "…" not in svg


def test_blueprint_fallback_sequence_extracts_participants_and_messages() -> None:
    spec = FigureSpec(
        chapter_id=13,
        section_id="13.2.2",
        occurrence=1,
        figure_id="fig-13-02",
        figure_type="sequence",
        title="图13-2 设备 DID 注册与验证流程",
        purpose="展示链上注册和链下验证。",
        layout="设备、合约和验证方三条泳道。",
        elements=[
            "设备1内部：生成 ECDSA 密钥对。",
            "设备1→智能合约：提交 registerDevice 交易。",
            "智能合约→区块链：写入 DIDRegistered 日志。",
            "设备1→设备2：发送 DID 与挑战签名。",
            "设备2→智能合约：查询 DID 文档。",
            "智能合约→设备2：返回 owner 与公钥哈希。",
            "设备2→设备1：返回验证结果。",
        ],
        relationships=["步骤2、3、5为链上操作，其余为链下操作。"],
        legend=["虚线=链上调用", "实线=链下消息"],
        caption="图13-2 展示设备身份的注册与验证闭环。",
        render_notes="标准时序图。",
        body_hash="hash",
    )

    blueprint = _fallback_blueprint(spec)

    assert [node["label"] for node in blueprint["nodes"]] == ["设备1", "智能合约", "区块链", "设备2"]
    assert len(blueprint["edges"]) == 6
    assert blueprint["edges"][0]["from"] == "actor-1"
    assert blueprint["edges"][0]["to"] == "actor-2"
    assert blueprint["edges"][0]["style"] == "dashed"
    assert blueprint["edges"][-1]["label"] == "返回验证结果"


def test_blueprint_renderer_draws_layered_comparison_columns() -> None:
    spec = FigureSpec(
        chapter_id=2,
        section_id="2.1.3",
        occurrence=1,
        figure_id="fig-02-03",
        figure_type="layered",
        title="图2-3 五层架构模型与传统四层架构的对比示意",
        purpose="对比四层和五层架构。",
        layout="并排两列分层布局。",
        elements=[],
        relationships=[],
        legend=["紫色=智能层。"],
        caption="图2-3 五层架构模型与经典四层架构的对比。",
        render_notes="HTML/SVG。",
        body_hash="hash",
        components=[
            {"id": "r1", "label": "四层-应用层", "type": "application", "group": "application_domain"},
            {"id": "r2", "label": "四层-平台层", "type": "platform", "group": "platform_domain"},
            {"id": "r3", "label": "四层-网络层", "type": "platform", "group": "platform_domain"},
            {"id": "r4", "label": "四层-感知层", "type": "edge", "group": "edge_domain"},
            {"id": "r5", "label": "五层-应用层", "type": "application", "group": "application_domain"},
            {"id": "r6", "label": "五层-智能层（新增）", "type": "ai", "group": "intelligence_domain", "priority": "primary"},
            {"id": "r7", "label": "五层-平台层", "type": "platform", "group": "platform_domain"},
            {"id": "r8", "label": "五层-网络层", "type": "platform", "group": "platform_domain"},
            {"id": "r9", "label": "五层-感知层", "type": "edge", "group": "edge_domain"},
        ],
    )

    svg = render_figure_blueprint_svg(spec, palette=spec_palette(), blueprint={})

    assert "四层" in svg
    assert "五层" in svg
    assert "智能层（新增）" in svg
    assert svg.count("应用层") >= 2


def test_figure_designer_opens_circuit_after_consecutive_failures() -> None:
    class FailingDesigner(FigureDesignerAgent):
        def __init__(self) -> None:
            super().__init__(object(), circuit_breaker_failures=2)  # type: ignore[arg-type]
            self.calls = 0

        def _request_svg_body(self, spec: FigureSpec, *, feedback: str) -> str:
            self.calls += 1
            raise TimeoutError("timeout")

    spec = FigureSpec(
        chapter_id=1,
        section_id="1.1.1",
        occurrence=1,
        figure_id="fig-01-01",
        figure_type="architecture",
        title="图1-1 平台架构",
        purpose="说明平台边界。",
        layout="分层架构。",
        elements=["设备层", "平台层"],
        relationships=["设备层接入平台层"],
        legend=["蓝色=平台"],
        caption="图1-1 展示平台架构。",
        render_notes="HTML/SVG 统一绘制。",
        body_hash="hash",
    )
    designer = FailingDesigner()

    for _ in range(4):
        designer.design(spec, palette=spec_palette())

    assert designer.calls == 2


def test_figure_designer_retries_failed_generation_before_fallback() -> None:
    class RetryingDesigner(FigureDesignerAgent):
        def __init__(self) -> None:
            super().__init__(object(), polish_rounds=1)  # type: ignore[arg-type]
            self.feedback: list[str] = []

        def _request_svg_body(self, spec: FigureSpec, *, feedback: str) -> str:
            self.feedback.append(feedback)
            if len(self.feedback) == 1:
                raise RuntimeError("矩形重叠")
            return '<g data-layout="architecture"><rect x="200" y="200" width="800" height="300"/></g>'

    spec = FigureSpec(
        chapter_id=1,
        section_id="1.1.1",
        occurrence=1,
        figure_id="fig-01-01",
        figure_type="architecture",
        title="图1-1 平台架构",
        purpose="说明平台边界。",
        layout="分层架构。",
        elements=["设备层", "平台层"],
        relationships=["设备层接入平台层"],
        legend=["蓝色=平台"],
        caption="图1-1 展示平台架构。",
        render_notes="HTML/SVG 统一绘制。",
        body_hash="hash",
    )
    designer = RetryingDesigner()

    design = designer.design(spec, palette=spec_palette(), feedback="避免连线穿框")

    assert design.notes == "AI 定制主体 + architecture-diagram 统一画布"
    assert len(designer.feedback) == 2
    assert "矩形重叠" in designer.feedback[1]
    assert "避免连线穿框" in designer.feedback[1]


def spec_palette() -> dict[str, str]:
    return {
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
