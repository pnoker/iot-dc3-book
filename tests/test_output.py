from __future__ import annotations

from typing import TYPE_CHECKING

from core.output import generate_output, get_template_environment
from core.state import BookState, ChapterContent, ChapterPlan, ForeshadowItem, PartPlan

if TYPE_CHECKING:
    from pathlib import Path


def test_output_templates_are_loaded_by_jinja() -> None:
    env = get_template_environment()

    assert "cover.md.j2" in env.list_templates()
    assert "foreshadow_report.md.j2" in env.list_templates()


def test_generate_output_renders_markdown_templates(tmp_path: Path) -> None:
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

    output_dir = generate_output(state, str(tmp_path), cfg)

    assert output_dir == str(tmp_path)
    assert (tmp_path / "00-封面.md").read_text(encoding="utf-8").startswith("# 测试书")
    assert "- IoT" in (tmp_path / "01-作者简介.md").read_text(encoding="utf-8")
    assert "- **基础篇**（第1章《总览》）" in (tmp_path / "03-导读.md").read_text(encoding="utf-8")
    assert (tmp_path / "05-基础篇" / "01-总览.md").read_text(encoding="utf-8") == "# 正文"
    assert "已回收: 1 / 1" in (tmp_path / "09-伏笔报告.md").read_text(encoding="utf-8")
