from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from core.figures import FigureAsset
from core.output import (
    _generate_cover_image,
    generate_markdown_output,
    generate_pdf_output,
    generate_word_output,
    get_template_environment,
)
from core.state import BookState, ChapterContent, ChapterPlan, ForeshadowItem, PartPlan


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
    assert (tmp_path / "00-封面.md").read_text(encoding="utf-8") == "![](cover.png)"
    assert "- IoT" in (tmp_path / "01-作者简介.md").read_text(encoding="utf-8")
    assert "- **基础篇**（第1章《总览》）" in (tmp_path / "03-导读.md").read_text(encoding="utf-8")
    assert (tmp_path / "05-基础篇" / "01-总览.md").read_text(encoding="utf-8") == "# 正文"
    assert "已回收: 1 / 1" in (tmp_path / "09-伏笔报告.md").read_text(encoding="utf-8")
    book_markdown = (tmp_path / "book.md").read_text(encoding="utf-8")
    assert book_markdown.startswith("![](cover.png)")
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
    markdown.write_text("# 标题\n\n# 目录\n\n- [第一章](#第一章)\n\n# 第一章\n\n正文", encoding="utf-8")
    reference = tmp_path / "reference.docx"
    reference.write_bytes(b"docx")
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], *, check: bool, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        assert check is False
        assert capture_output is True
        assert text is True
        source = Path(cmd[1])
        assert source == tmp_path / ".book_for_word.md"
        cleaned = source.read_text(encoding="utf-8")
        assert "# 目录" not in cleaned
        assert "# 第一章" in cleaned
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("core.output.shutil.which", lambda name: "/usr/local/bin/pandoc")
    monkeypatch.setattr("core.output.subprocess.run", fake_run)

    word_file = generate_word_output(markdown, tmp_path / "book.docx", reference_docx=reference, pandoc_bin="pandoc")

    assert word_file == str(tmp_path / "book.docx")
    assert calls == [
        [
            "/usr/local/bin/pandoc",
            str(tmp_path / ".book_for_word.md"),
            "--from",
            "markdown+pipe_tables+fenced_code_blocks+yaml_metadata_block",
            "--to",
            "docx",
            "--output",
            str(tmp_path / "book.docx"),
            "--resource-path",
            os.pathsep.join([str(tmp_path), str(tmp_path.parent)]),
            "--toc",
            "--toc-depth=3",
            "--reference-doc",
            str(reference),
        ]
    ]
    assert not (tmp_path / ".book_for_word.md").exists()


def test_generate_word_output_requires_pandoc(tmp_path: Path, monkeypatch) -> None:
    markdown = tmp_path / "book.md"
    markdown.write_text("# 标题", encoding="utf-8")
    monkeypatch.setattr("core.output.shutil.which", lambda name: None)

    with pytest.raises(RuntimeError, match="未找到 pandoc"):
        generate_word_output(markdown, tmp_path / "book.docx")


def test_generate_pdf_output_merges_cover_and_cleans_temporary_files(tmp_path: Path, monkeypatch) -> None:
    draft_dir = tmp_path / "draft"
    draft_dir.mkdir()
    markdown = draft_dir / "book.md"
    markdown.write_text("![](cover.png)\n\n# 第一章\n\n正文", encoding="utf-8")
    cover_html = tmp_path / "cover.html"
    cover_html.write_text("<html><body>封面</body></html>", encoding="utf-8")
    css_file = tmp_path / "pdf_style.css"
    css_file.write_text("@page { size: A4; }", encoding="utf-8")
    pdf_file = draft_dir / "book.pdf"
    pandoc_inputs: list[str] = []
    pandoc_css: list[str] = []
    pandoc_cwds: list[object] = []

    def write_single_page_pdf(path: Path) -> None:
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        with path.open("wb") as output:
            writer.write(output)

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["check"] is False
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        if cmd[0] == "/usr/local/bin/pandoc":
            source = Path(cmd[1])
            pandoc_inputs.append(source.read_text(encoding="utf-8"))
            pandoc_css.append(cmd[cmd.index("--css") + 1])
            pandoc_cwds.append(kwargs.get("cwd"))
            Path(cmd[cmd.index("-o") + 1]).write_text("<html><body>正文</body></html>", encoding="utf-8")
        else:
            output_arg = next(arg for arg in cmd if arg.startswith("--print-to-pdf="))
            write_single_page_pdf(Path(output_arg.split("=", 1)[1]))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("core.output.shutil.which", lambda name: "/usr/local/bin/pandoc")
    monkeypatch.setattr("core.output.subprocess.run", fake_run)

    result = generate_pdf_output(
        markdown,
        pdf_file,
        chrome_bin="/Applications/Google Chrome",
        pandoc_bin="pandoc",
        cover_html=cover_html,
        css_file=css_file,
    )

    assert result == str(pdf_file)
    assert len(PdfReader(pdf_file).pages) == 2
    assert pandoc_inputs == ["# 第一章\n\n正文"]
    assert pandoc_css == ["../pdf_style.css"]
    assert pandoc_cwds == [None]
    assert not (draft_dir / ".book_body.md").exists()
    assert not (draft_dir / ".book_body.pdf").exists()
    assert not (draft_dir / ".book_cover.pdf").exists()


def test_generate_cover_image_converts_pdf_to_png_and_cleans_temporary_file(
        tmp_path: Path,
        monkeypatch,
) -> None:
    cover_html = tmp_path / "cover.html"
    cover_html.write_text("<html><body>封面</body></html>", encoding="utf-8")
    output_png = tmp_path / "cover.png"
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        assert kwargs["check"] is False
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        if cmd[0] == "/Applications/Google Chrome":
            output_arg = next(arg for arg in cmd if arg.startswith("--print-to-pdf="))
            writer = PdfWriter()
            writer.add_blank_page(width=595, height=842)
            with Path(output_arg.split("=", 1)[1]).open("wb") as output:
                writer.write(output)
        elif cmd[0] == "/usr/bin/pdftoppm":
            Path(cmd[-1]).with_suffix(".png").write_bytes(b"png")
        else:
            Path(cmd[-1]).write_bytes(b"png")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("core.output.shutil.which", lambda name: f"/usr/bin/{name}" if name in {"pdftoppm", "sips"} else None)
    monkeypatch.setattr("core.output.subprocess.run", fake_run)

    _generate_cover_image(cover_html, output_png, chrome_bin="/Applications/Google Chrome")

    assert output_png.read_bytes() == b"png"
    assert len(calls) == 2
    assert calls[1] == [
        "/usr/bin/pdftoppm",
        "-png",
        "-r",
        "300",
        "-singlefile",
        str(tmp_path / ".cover_tmp.pdf"),
        str(tmp_path / "cover"),
    ]
    assert not (tmp_path / ".cover_tmp.pdf").exists()
