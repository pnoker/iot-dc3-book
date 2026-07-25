"""
手稿文件系统读取 —— 从 book/manuscript/ 读取手稿 Markdown。
"""

from __future__ import annotations

import re
from pathlib import Path

from book_builder.config import PartConfig
from book_builder.log import get_logger

logger = get_logger("manuscript")

# 匹配 section 文件名: X.Y.Z.md
_SECTION_FILE_RE = re.compile(r"^\d+\.\d+\.\d+$")


def load_manuscript(
    parts: list[PartConfig],
    manuscript_dir: str | Path = "book/manuscript",
) -> dict[int, str]:
    """
    遍历 parts 中的章节，读取手稿文件。

    优先读取 chapter-XX/chapter.md（完整章内容）；
    若不存在或为空，则从 chapter-XX/X.Y.Z.md 节文件拼接。

    Returns:
        dict[chapter_id, assembled_markdown]
    """
    base = Path(manuscript_dir)
    chapters: dict[int, str] = {}
    for part in parts:
        for chapter in part.chapters:
            chapter_dir = base / f"chapter-{chapter.id:02d}"
            chapter_file = chapter_dir / "chapter.md"
            if chapter_file.exists():
                content = chapter_file.read_text(encoding="utf-8").strip()
                if content:
                    chapters[chapter.id] = content
                    logger.debug("第%d章 从 chapter.md 读取 (%d 字符)", chapter.id, len(content))
                    continue
            # 降级：从小节文件拼接
            content = _assemble_from_sections(chapter_dir)
            if content:
                chapters[chapter.id] = content
                logger.debug("第%d章 从节文件拼接 (%d 字符)", chapter.id, len(content))
            else:
                logger.warning("第%d章(%s) 缺少手稿文件: %s", chapter.id, chapter.title, chapter_dir)
    return chapters


def _sort_key(filename: str) -> tuple[int, ...]:
    """将 X.Y.Z 转为可排序的 tuple。"""
    try:
        return tuple(int(part) for part in filename.split("."))
    except ValueError:
        return (9999,)


def _assemble_from_sections(chapter_dir: Path) -> str:
    """按 section_id 排序，拼接所有 X.Y.Z.md 文件。"""
    if not chapter_dir.exists():
        return ""
    section_files = sorted(
        [f for f in chapter_dir.glob("*.md") if _SECTION_FILE_RE.match(f.stem) and f.name != "chapter.md"],
        key=lambda f: _sort_key(f.stem),
    )
    if not section_files:
        return ""
    parts = []
    for sf in section_files:
        content = sf.read_text(encoding="utf-8").strip()
        if content:
            parts.append(content)
    return "\n\n".join(parts)
