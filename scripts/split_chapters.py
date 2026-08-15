#!/usr/bin/env python3
"""把 book/manuscript/chapter-XX/chapter.md 拆分为 X.Y.md 二级节文件。

每个 H2（##）拆成一个二级节文件；代码块内的 #/##/### 不视为标题；
节内的 H3/H4 子标题与正文原样保留在节文件内；
章引言（H1 后、第一个 H2 前的内容）写入 _intro.md；
原 chapter.md 归档到 book/manuscript/_archive/。

用法：.venv/bin/python scripts/split_chapters.py [--dry-run]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANUSCRIPT = ROOT / "book" / "manuscript"
ARCHIVE = MANUSCRIPT / "_archive"

H1_RE = re.compile(r"^#\s+(.+)$")
H2_RE = re.compile(r"^##\s+(.+)$")
FENCE_RE = re.compile(r"^\s*```")


def parse_chapter(text: str) -> dict:
    lines = text.split("\n")
    in_code = False
    h1 = ""
    intro: list[str] = []
    sections: list[dict] = []
    cur_section: dict | None = None

    def append(line: str) -> None:
        if cur_section is not None:
            cur_section["body"].append(line)
        else:
            intro.append(line)

    for line in lines:
        if FENCE_RE.match(line):
            append(line)
            in_code = not in_code
            continue
        if in_code:
            append(line)
            continue
        m = H1_RE.match(line)
        if m:
            h1 = m.group(1).strip()
            continue
        m = H2_RE.match(line)
        if m:
            cur_section = {"title": m.group(1).strip(), "body": []}
            sections.append(cur_section)
            continue
        # H3/H4/正文归入当前节
        append(line)

    return {"h1": h1, "intro": intro, "sections": sections}


def h2_stem(title: str) -> str | None:
    m = re.match(r"^(\d+\.\d+)(?=\s|$)", title)
    return m.group(1) if m else None


def render_frontmatter(section_title: str) -> str:
    if not section_title:
        return ""
    escaped = section_title.replace('"', '\\"')
    return f'---\nsection: "{escaped}"\n---\n\n'


def render_section(section: dict) -> str:
    parts = [render_frontmatter(section["title"])]
    parts.append(f"## {section['title']}\n")
    parts.append("\n".join(section["body"]))
    return "\n".join(parts).rstrip() + "\n"


def split_chapter(chapter_dir: Path, dry_run: bool = False) -> dict:
    chapter_md = chapter_dir / "chapter.md"
    if not chapter_md.exists():
        return {"status": "no-chapter.md"}
    text = chapter_md.read_text(encoding="utf-8")
    parsed = parse_chapter(text)

    n_h2 = len(parsed["sections"])
    intro_text = "\n".join(parsed["intro"]).strip()

    report = {
        "chapter": chapter_dir.name,
        "h1": parsed["h1"],
        "n_h2": n_h2,
        "has_intro": bool(intro_text),
        "files": [],
        "status": "ok",
    }

    if dry_run:
        for s in parsed["sections"]:
            stem = h2_stem(s["title"]) or s["title"]
            report["files"].append(f"{stem}.md")
        if report["has_intro"]:
            report["files"].append("_intro.md")
        return report

    # 实际写入：先清理旧分节文件与章引言（避免编号变更后旧文件残留）
    for old in list(chapter_dir.glob("[0-9]*.md")) + list(chapter_dir.glob("_intro.md")):
        old.unlink()
    for s in parsed["sections"]:
        stem = h2_stem(s["title"])
        if not stem:
            print(f"⚠️  {chapter_dir.name}: 节标题缺少编号，跳过 → {s['title']}")
            continue
        content = render_section(s)
        (chapter_dir / f"{stem}.md").write_text(content, encoding="utf-8")
        report["files"].append(f"{stem}.md")
    if intro_text:
        (chapter_dir / "_intro.md").write_text(intro_text + "\n", encoding="utf-8")
        report["files"].append("_intro.md")

    # 归档 chapter.md
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    chapter_md.rename(ARCHIVE / f"{chapter_dir.name}.md")
    report["archived"] = str(ARCHIVE / f"{chapter_dir.name}.md")
    return report


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    chapters = sorted(MANUSCRIPT.glob("chapter-*"))
    total_h2 = 0
    for ch in chapters:
        rep = split_chapter(ch, dry_run=dry_run)
        if rep["status"] != "ok":
            print(f"{rep['chapter']}: 跳过（{rep['status']}）")
            continue
        total_h2 += rep["n_h2"]
        verb = "将拆分" if dry_run else "已拆分"
        print(f"{verb} {rep['chapter']}: {rep['n_h2']} 节"
              + ("（含章引言）" if rep["has_intro"] else ""))
    print(f"\n合计 {len(chapters)} 章 / {total_h2} 个二级节文件"
          + ("（dry-run，未写入）" if dry_run else ""))


if __name__ == "__main__":
    main()
