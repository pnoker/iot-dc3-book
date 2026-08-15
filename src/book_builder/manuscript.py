"""
手稿文件系统读取 —— 从 book/manuscript/ 读取手稿 Markdown。

手稿按二级节组织：chapter-XX/X.Y.md（每个二级标题 H2 一个节文件），
文件 frontmatter 记录节标题（section），正文保留 H2 标题与节内 H3/H4。
本模块拼接 H1 章标题 + 章引言 + 各节文件，恢复完整章结构。
"""

from __future__ import annotations

import re
from pathlib import Path

from book_builder.config import PartConfig
from book_builder.log import get_logger

logger = get_logger("manuscript")

# 匹配节文件名: X.Y.md
_SECTION_FILE_RE = re.compile(r"^\d+\.\d+$")
# frontmatter 块
_FM_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)


def load_manuscript(
    parts: list[PartConfig],
    manuscript_dir: str | Path = "book/manuscript",
) -> dict[int, str]:
    """
    遍历 parts 中的章节，读取手稿文件。

    优先从 chapter-XX/X.Y.md 节文件组装（每个二级标题一个节文件，
    按文件名排序拼接，恢复 H1 章 + H2 节 + 节内 H3/H4 结构）；
    若目录下无节文件，则降级读取 chapter-XX/chapter.md（旧版整章）。

    Returns:
        dict[chapter_id, assembled_markdown]
    """
    base = Path(manuscript_dir)
    chapters: dict[int, str] = {}
    for part in parts:
        for chapter in part.chapters:
            chapter_dir = base / f"chapter-{chapter.id:02d}"
            content = _assemble_from_sections(chapter_dir, chapter.id, chapter.title)
            if content:
                chapters[chapter.id] = content
                logger.debug("第%d章 从节文件组装 (%d 字符)", chapter.id, len(content))
                continue
            # 降级：整章 chapter.md（旧版手稿）
            chapter_file = chapter_dir / "chapter.md"
            if chapter_file.exists():
                content = chapter_file.read_text(encoding="utf-8").strip()
                if content:
                    chapters[chapter.id] = content
                    logger.debug("第%d章 从 chapter.md 读取 (%d 字符)", chapter.id, len(content))
                    continue
            logger.warning("第%d章(%s) 缺少手稿文件: %s", chapter.id, chapter.title, chapter_dir)
    return chapters


def _sort_key(filename: str) -> tuple[int, ...]:
    """将 X.Y 转为可排序的 tuple。"""
    try:
        return tuple(int(part) for part in filename.split("."))
    except ValueError:
        return (9999,)


def _strip_frontmatter(text: str) -> str:
    """剥离 frontmatter，返回正文（节标题 + 节内内容）。"""
    m = _FM_RE.match(text)
    return text[m.end():].strip() if m else text.strip()


def _assemble_from_sections(chapter_dir: Path, chapter_id: int, chapter_title: str) -> str:
    """拼接节文件为完整章 Markdown（H1 章 + 章引言 + 各节 H2 正文）。"""
    if not chapter_dir.exists():
        return ""
    section_files = sorted(
        [f for f in chapter_dir.glob("*.md") if _SECTION_FILE_RE.match(f.stem)],
        key=lambda f: _sort_key(f.stem),
    )
    if not section_files:
        return ""
    lines = [f"# 第{chapter_id}章 {chapter_title}"]
    # 章引言（H1 后、第一个 H2 前的内容）
    intro_file = chapter_dir / "_intro.md"
    if intro_file.exists():
        intro = intro_file.read_text(encoding="utf-8").strip()
        if intro:
            lines.append("")
            lines.append(intro)
    for sf in section_files:
        body = _strip_frontmatter(sf.read_text(encoding="utf-8"))
        lines.append("")
        lines.append(body)
    return "\n".join(lines).strip()
