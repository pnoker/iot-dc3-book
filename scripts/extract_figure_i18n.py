#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抽取插图 SVG 内的中文文本，生成/补全图注册表的英文标注（labels.en）。

图注册表：book/figures/chapter-XX/{fig-id}.yaml（spec + caption.zh/en + labels.en）。
改图后重跑本脚本可同步 labels.en 的键（已有译文保留，新增键留空待译）。

用法:
  uv run python scripts/extract_figure_i18n.py fig-01-05            # 打印该图的 labels.en 桩
  uv run python scripts/extract_figure_i18n.py fig-01-05 --write    # 写入注册表（不覆盖已填译文）
  uv run python scripts/extract_figure_i18n.py chapter-01 --write   # 整章批量
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

from fig_theme import (  # noqa: E402
    FIGURES_DIR, extract_figure_texts, load_figure_registry,
)

FIG_ID_RE = re.compile(r"^fig-\d{2}-\d{2}$")


def yaml_str(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def stub_yaml(fig_id: str) -> str:
    reg = load_figure_registry(fig_id)
    labels = reg.get("labels", {}).get("en", {}) if isinstance(reg.get("labels"), dict) else {}
    lines = [f"# {fig_id} labels.en —— 图内标注翻译（键为 SVG 中文原文，改图后重跑本脚本同步）"]
    for zh in extract_figure_texts(fig_id):
        en = labels.get(zh, "")
        lines.append(f"{yaml_str(zh)}: {yaml_str(en)}")
    return "\n".join(lines) + "\n"


def write_stub(fig_id: str) -> bool:
    reg_path = FIGURES_DIR / f"chapter-{fig_id.split('-')[1]}" / f"{fig_id}.yaml"
    if not reg_path.exists():
        print(f"✗ 无注册表: {reg_path}")
        return False
    reg = load_figure_registry(fig_id)
    labels = reg.get("labels", {}).get("en", {}) if isinstance(reg.get("labels"), dict) else {}
    texts = extract_figure_texts(fig_id)
    if set(texts) <= set(labels):
        return False  # 无新增条目
    reg.setdefault("labels", {})["en"] = {zh: labels.get(zh, "") for zh in texts}
    reg_path.write_text(
        yaml.safe_dump(reg, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8"
    )
    return True


def fig_ids_of(chapter: str) -> list[str]:
    no = int(chapter.replace("chapter-", "").replace("ch", ""))
    ch_dir = FIGURES_DIR / f"chapter-{no:02d}"
    return sorted(f.stem for f in ch_dir.glob("fig-*.html"))


def main() -> None:
    ap = argparse.ArgumentParser(description="生成/补全图注册表英文标注")
    ap.add_argument("target", help="figure id（fig-01-05）或章目录（chapter-01 / 01）")
    ap.add_argument("--write", action="store_true", help="写入注册表（默认仅打印）")
    args = ap.parse_args()

    targets = [args.target] if FIG_ID_RE.match(args.target) else fig_ids_of(args.target)
    for fig_id in targets:
        if args.write:
            changed = write_stub(fig_id)
            print(f"{'✓ 更新' if changed else '· 无变化'}  {fig_id} labels.en")
        else:
            print(stub_yaml(fig_id))


if __name__ == "__main__":
    main()
