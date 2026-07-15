"""一次性修复脚本：从完整的 section_contents 重建残缺的 ChapterContent.markdown。

背景：section_contents（234 小节）正文完整，但派生的 ChapterContent（章节合稿）
普遍残缺（旧合稿产物），导致 output 导出丢内容。本脚本绕过 LLM assembler，
直接按蓝图顺序拼接小节正文，重建 ChapterContent，再由 write export 正式导出。

用法：
  python .tmp/reassemble_chapters.py          # dry-run，仅报告
  APPLY=1 python .tmp/reassemble_chapters.py  # 实际写回 book-1.json
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

BOOK = Path(".data/write/book-1.json")
APPLY = os.environ.get("APPLY") == "1"


def normalize(markdown: str) -> str:
    """复刻 workflow._normalize_markdown_output：去掉 LLM 偶发的 markdown 围栏前缀。"""
    text = markdown.strip()
    fence = re.search(r"```(?:markdown|md)\s*\n", text, flags=re.IGNORECASE)
    heading = re.search(r"^#{1,6}\s+", text, flags=re.MULTILINE)
    if fence and (heading is None or fence.start() < heading.start()):
        text = text[fence.end():].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    return text


def count_words(md: str) -> int:
    return len(re.findall(r"[一-鿿]", md)) + len(re.findall(r"[A-Za-z]+", md))


def build_rows(st: dict) -> list[tuple]:
    """对每章按蓝图顺序拼接 section_contents，返回 (cid, old_len, new_md, n_sections, missing, chapter_content)。"""
    sec_map: dict[str, str] = {}
    for it in st.get("section_contents", []):
        sid = it.get("section_id")
        md = it.get("markdown") or ""
        if sid:
            sec_map[sid] = md

    rows = []
    for part in st["parts"]:
        for ch in part["chapters"]:
            cid = ch["id"]
            title = ch["title"]
            blueprint_sections = ch.get("sections", [])
            pieces = [f"# 第{cid}章 {title}"]
            missing: list[str] = []
            prev_l2: str | None = None
            for s in blueprint_sections:
                sid = s["id"]
                l2 = ".".join(sid.split(".")[:2])
                if l2 != prev_l2:
                    # 二级标题：编号 + parent_title（剥掉其自带的编号前缀）
                    pt = re.sub(r"^\d+\.\d+\s*", "", s.get("parent_title", "")).strip()
                    pieces.append(f"## {l2} {pt}".strip())
                    prev_l2 = l2
                md = sec_map.get(sid, "")
                if md.strip():
                    pieces.append(md.strip())
                else:
                    missing.append(sid)
            new_md = normalize("\n\n".join(pieces))
            cc = next((c for c in st["chapters"] if c.get("chapter_id") == cid), None)
            old_len = len(cc["markdown"]) if cc else 0
            rows.append((cid, old_len, new_md, len(blueprint_sections), missing, cc))
    return rows


def main() -> int:
    if not BOOK.exists():
        print(f"找不到 checkpoint: {BOOK}", file=sys.stderr)
        return 1

    d = json.loads(BOOK.read_text(encoding="utf-8"))
    st = d["state"]
    rows = build_rows(st)

    print(f"模式: {'✏️ APPLY（写回）' if APPLY else '🔍 dry-run（只报告）'}")
    print(f"{'章':>4} {'旧md':>8} {'新md':>8} {'蓝图节':>6} {'缺正文':>6}  变化")
    any_missing = False
    for cid, ol, new_md, ns, miss, cc in rows:
        nl = len(new_md)
        delta = nl - ol
        if miss:
            any_missing = True
        grow = "↑增大" if delta > 100 else ("=持平" if abs(delta) <= 100 else "↓缩小")
        mark = f"  ⚠️ 缺正文 {miss}" if miss else ""
        print(f"第{cid:>2} {ol:>8} {nl:>8} {ns:>6} {len(miss):>6}  {grow}{mark}")

    if any_missing:
        print("\n⚠️ 有小节在 section_contents 中缺正文，重建后这些章仍不完整，需先补写。")

    if not APPLY:
        print("\n（dry-run 未写回。确认无误后用 APPLY=1 重跑。）")
        return 0

    bak = BOOK.with_name(
        f"{BOOK.stem}.before-reassemble-{time.strftime('%Y%m%d-%H%M%S')}{BOOK.suffix}"
    )
    shutil.copy2(BOOK, bak)
    for cid, ol, new_md, ns, miss, cc in rows:
        if cc is None:
            print(f"  ⚠️ 第{cid}章无 ChapterContent 条目，跳过")
            continue
        cc["markdown"] = new_md
        cc["word_count"] = count_words(new_md)
    BOOK.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 已写回 {BOOK}，备份: {bak}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
