from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

import pytest

from core.figures import FigureAsset
from core.output import generate_markdown_output, generate_word_output, get_template_environment
from core.state import BookState, ChapterContent, ChapterPlan, ForeshadowItem, PartPlan

if TYPE_CHECKING:
    from pathlib import Path


def test_output_templates_are_loaded_by_jinja() -> None:
    env = get_template_environment()

    assert "cover.md.j2" in env.list_templates()
    assert "foreshadow_report.md.j2" in env.list_templates()


def test_generate_markdown_output_renders_structured_files_and_book_markdown(tmp_path: Path) -> None:
    state = BookState(
        book_title="测试书",
        book_subtitle="专业写作",
        author="作者A",
        parts=[PartPlan(name="基础篇", prefix="一", chapters=[ChapterPlan(id=1, title="总览")])],
        chapters=[ChapterContent(chapter_id=1, title="总览", markdown="# 正文")],
        foreshadows=[
            ForeshadowItem(
                id="F1",
                description="前文伏笔",
                planted_chapter=1,
                planned_resolve_chapter=2,
                status="resolved",
            )
        ],
    )
    cfg = {
        "author": {
            "profile": {
                "name": "作者A",
                "title": "IoT 架构师",
                "bio": "长期从事工业物联网。",
                "expertise": ["IoT", "Agent"],
                "project": "IoT DC3",
                "project_url": "https://example.test",
                "project_description": "开源物联网平台。",
            },
            "preface": {"title": "序", "content": "这是序言。", "theme": "面向实践。"},
        }
    }

    result = generate_markdown_output(state, str(tmp_path), cfg)

    assert result["output_dir"] == str(tmp_path)
    assert result["book_markdown"] == str(tmp_path / "book.md")
    assert (tmp_path / "00-封面.md").read_text(encoding="utf-8").startswith("# 测试书")
    assert "- IoT" in (tmp_path / "01-作者简介.md").read_text(encoding="utf-8")
    assert "- **基础篇**（第1章《总览》）" in (tmp_path / "03-导读.md").read_text(encoding="utf-8")
    assert (tmp_path / "05-基础篇" / "01-总览.md").read_text(encoding="utf-8") == "# 正文"
    assert "已回收: 1 / 1" in (tmp_path / "09-伏笔报告.md").read_text(encoding="utf-8")
    book_markdown = (tmp_path / "book.md").read_text(encoding="utf-8")
    assert "# 测试书" in book_markdown
    assert "# 一、基础篇" in book_markdown
    assert "# 正文" in book_markdown
    assert "伏笔报告" not in book_markdown


def test_generate_markdown_output_replaces_book_figures_with_png(tmp_path: Path) -> None:
    figure_block = '''```book-figure
id: "fig-01-01"
type: "architecture"
title: "图1-1 架构"
purpose: "说明架构。"
layout: "分层。"
elements:
  - "设备层"
relationships:
  - "设备到平台"
legend:
  - "蓝色=平台"
caption: "图1-1 展示架构。"
render_notes: "HTML/SVG。"
```'''
    state = BookState(
        book_title="测试书",
        parts=[PartPlan(name="基础篇", prefix="一", chapters=[ChapterPlan(id=1, title="总览")])],
        chapters=[ChapterContent(chapter_id=1, title="总览", markdown=f"# 第1章 总览\n\n{figure_block}")],
    )
    asset = FigureAsset(
        chapter_id=1,
        section_id="1.1.1",
        occurrence=1,
        figure_id="fig-01-01",
        figure_type="architecture",
        title="图1-1 架构",
        caption="图1-1 展示架构。",
        svg_path="output/figures/chapter-01/fig-01-01.svg",
        html_path="output/figures/chapter-01/fig-01-01.html",
        png_path="output/figures/chapter-01/fig-01-01.png",
        markdown_path="figures/chapter-01/fig-01-01.png",
        body_hash="hash",
    )

    generate_markdown_output(state, str(tmp_path), {}, figure_assets=[asset])

    chapter_markdown = (tmp_path / "05-基础篇" / "01-总览.md").read_text(encoding="utf-8")
    book_markdown = (tmp_path / "book.md").read_text(encoding="utf-8")
    assert "```book-figure" not in chapter_markdown
    assert "![图1-1 架构](../figures/chapter-01/fig-01-01.png){width=15cm}" in chapter_markdown
    assert "![图1-1 架构](figures/chapter-01/fig-01-01.png){width=15cm}" in book_markdown


def test_generate_word_output_invokes_pandoc(tmp_path: Path, monkeypatch) -> None:
    markdown = tmp_path / "book.md"
    markdown.write_text("# 标题\n\n正文", encoding="utf-8")
    reference = tmp_path / "reference.docx"
    reference.write_bytes(b"docx")
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], *, check: bool, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        assert check is False
        assert capture_output is True
        assert text is True
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("core.output.shutil.which", lambda name: "/usr/local/bin/pandoc")
    monkeypatch.setattr("core.output.subprocess.run", fake_run)

    word_file = generate_word_output(markdown, tmp_path / "book.docx", reference_docx=reference, pandoc_bin="pandoc")

    assert word_file == str(tmp_path / "book.docx")
    assert calls == [
        [
            "/usr/local/bin/pandoc",
            str(markdown),
            "--from",
            "markdown+pipe_tables+fenced_code_blocks+yaml_metadata_block",
            "--to",
            "docx",
            "--output",
            str(tmp_path / "book.docx"),
            "--resource-path",
            os.pathsep.join([str(tmp_path), str(tmp_path.parent)]),
            "--reference-doc",
            str(reference),
        ]
    ]


def test_generate_word_output_requires_pandoc(tmp_path: Path, monkeypatch) -> None:
    markdown = tmp_path / "book.md"
    markdown.write_text("# 标题", encoding="utf-8")
    monkeypatch.setattr("core.output.shutil.which", lambda name: None)

    with pytest.raises(RuntimeError, match="未找到 pandoc"):
        generate_word_output(markdown, tmp_path / "book.docx")
