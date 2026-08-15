"""
手稿文件系统读取 —— 从 book/manuscript/ 读取手稿 Markdown。

手稿按小节组织：chapter-XX/X.Y.Z.md（每个三级标题一个小节文件），
文件 frontmatter 记录所属节标题（section）。本模块按节分组、恢复章/节/小节结构。
"""

from __future__ import annotations

import re
from pathlib import Path

from book_builder.config import PartConfig
from book_builder.log import get_logger

logger = get_logger("manuscript")

# 匹配小节文件名: X.Y.Z.md
_SECTION_FILE_RE = re.compile(r"^\d+\.\d+\.\d+$")
# frontmatter 块
_FM_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)


def load_manuscript(
    parts: list[PartConfig],
    manuscript_dir: str | Path = "book/manuscript",
) -> dict[int, str]:
    """
    遍历 parts 中的章节，读取手稿文件。

    优先从 chapter-XX/X.Y.Z.md 小节文件组装（每个三级标题一个小节文件，
    按 frontmatter 的 section 归节、恢复章/节/小节三级结构）；
    若目录下无小节文件，则降级读取 chapter-XX/chapter.md（旧版整章）。

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
    """将 X.Y.Z 转为可排序的 tuple。"""
    try:
        return tuple(int(part) for part in filename.split("."))
    except ValueError:
        return (9999,)


def _strip_frontmatter(text: str) -> str:
    """剥离 frontmatter，返回正文（小节标题 + 内容）。"""
    m = _FM_RE.match(text)
    return text[m.end():].strip() if m else text.strip()


def _parse_section(text: str) -> str:
    """从 frontmatter 提取 section（所属节标题，如 "1.1 工业软件的演进与局限"）。"""
    m = _FM_RE.match(text)
    if not m:
        return ""
    sm = re.search(r'^section:\s*"?([^"\n]+)"?\s*$', m.group(1), re.M)
    return sm.group(1).strip() if sm else ""


def _assemble_from_sections(chapter_dir: Path, chapter_id: int, chapter_title: str) -> str:
    """按节分组，组装小节文件为完整章 Markdown（H1 章 + H2 节 + H3 小节）。"""
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
    # 按节分组
    sections: dict[str, list[str]] = {}
    order: list[str] = []
    for sf in section_files:
        text = sf.read_text(encoding="utf-8")
        body = _strip_frontmatter(text)
        section = _parse_section(text)
        if section not in sections:
            sections[section] = []
            order.append(section)
        sections[section].append(body)
    for section in order:
        lines.append("")
        lines.append(f"## {section}")
        for body in sections[section]:
            lines.append("")
            lines.append(body)
    return "\n".join(lines).strip()
