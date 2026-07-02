"""
输出模块 - 将书稿生成为结构化的 Markdown 文件
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.log import get_logger
from core.state import BookState

logger = get_logger("output")


@lru_cache(maxsize=1)
def get_template_environment() -> Environment:
    """返回 Markdown 输出模板环境。"""
    template_dir = Path(__file__).resolve().parent / "templates"
    return Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def generate_output(state: BookState, output_dir: str, cfg: dict[str, Any] | None = None) -> str:
    """
    将全书内容输出为层级化的 Markdown 文件结构。

    输出结构：
    output/
    ├── 00-封面.md
    ├── 01-作者简介.md
    ├── 02-序.md
    ├── 03-导读.md
    ├── 04-目录.md
    ├── 05-基础篇/
    │   ├── 01-xxx.md
    │   └── ...
    ├── 06-技术篇/
    ├── 07-应用篇/
    ├── 08-附录.md
    ├── 09-伏笔报告.md
    └── 10-终审报告.md
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    env = get_template_environment()
    cfg = cfg or {}

    _write_file(out / "00-封面.md", _render(env, "cover.md.j2", state=state))

    author_cfg = cfg.get("author", {})
    profile = author_cfg.get("profile")
    if profile:
        _write_file(out / "01-作者简介.md", _render(env, "author_profile.md.j2", profile=profile))

    preface = author_cfg.get("preface")
    if preface:
        _write_file(out / "02-序.md", _render(env, "preface.md.j2", preface=preface))
        _write_file(out / "03-导读.md", _render(env, "reading_guide.md.j2", preface=preface, state=state))

    toc_content = state.toc_markdown or _render(env, "toc.md.j2", state=state)
    _write_file(out / "04-目录.md", toc_content)

    part_dirs = ["05-基础篇", "06-技术篇", "07-应用篇"]
    for part_idx, part in enumerate(state.parts):
        dir_name = part_dirs[part_idx] if part_idx < len(part_dirs) else f"{part_idx + 1:02d}-{part.name}"
        part_dir = out / dir_name
        part_dir.mkdir(parents=True, exist_ok=True)
        for chapter in part.chapters:
            content = state.get_chapter_content(chapter.id)
            if content:
                filename = f"{chapter.id:02d}-{chapter.title}.md"
                _write_file(part_dir / filename, content.markdown)

    _write_file(out / "08-附录.md", _render(env, "appendix.md.j2"))
    _write_file(
        out / "09-伏笔报告.md",
        _render(
            env,
            "foreshadow_report.md.j2",
            state=state,
            resolved_count=sum(1 for item in state.foreshadows if item.status == "resolved"),
        ),
    )

    if state.final_report:
        _write_file(out / "10-终审报告.md", state.final_report)

    logger.info("输出完成: %s", out)
    return str(out)


def _render(env: Environment, template_name: str, **context: Any) -> str:
    return env.get_template(template_name).render(**context)


def _write_file(path: Path, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.debug("已生成: %s", path)
