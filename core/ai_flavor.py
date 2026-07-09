"""AI 腔检测：用确定性规则找出让文字"一看就是 AI 写的"的显性痕迹。

只做廉价、可重复的正则/统计检测（套话短语 + 加粗滥用），作为软提示反馈给作者，
不参与质量门的硬阻断判定。结构性 AI 味（空心论述、节奏均匀等）由写作侧 prompt 治本，
不在此检测。
"""

from __future__ import annotations

import re

from core.wordcount import count_words

# AI 高频套话：开场/过渡/空心总结类，命中即提示作者改写。
_CLICHE_PATTERNS: tuple[str, ...] = (
    r"在当今[^，。]*?(时代|社会|背景下)",
    r"随着[^，。]*?的(不断)?(发展|推进|深入|普及)",
    r"综上所述",
    r"总而言之",
    r"值得(注意|一提)的是",
    r"不难(发现|看出|想象)",
    r"众所周知",
    r"毋庸置疑",
    r"奠定了[^，。]*?基础",
    r"具有(重要|重大|深远)(的)?(意义|价值|影响)",
    r"发挥着[^，。]*?(重要|关键)(的)?作用",
    r"扮演着[^，。]*?(重要|关键)(的)?角色",
)
_CLICHE_RE = re.compile("|".join(f"(?:{p})" for p in _CLICHE_PATTERNS))

# 加粗标记（成对 **…**）；密度过高是典型 AI 排版腔。
_BOLD_RE = re.compile(r"\*\*[^*\n]+\*\*")

# 每千字加粗数的软上限。
_BOLD_PER_KILO_LIMIT = 8.0


def detect_ai_flavor(markdown: str) -> list[str]:
    """检测 AI 腔痕迹，返回人类可读的问题描述列表（空列表表示未发现）。"""
    issues: list[str] = []

    hits = [m.group(0) for m in _CLICHE_RE.finditer(markdown)]
    if hits:
        uniq = list(dict.fromkeys(hits))
        issues.append(f"发现 {len(hits)} 处 AI 套话（如：{'、'.join(uniq[:5])}），建议改写为具体、有信息量的表达。")

    words = count_words(markdown)
    bold_count = len(_BOLD_RE.findall(markdown))
    if words >= 500 and bold_count / (words / 1000) > _BOLD_PER_KILO_LIMIT:
        per_kilo = bold_count / (words / 1000)
        issues.append(
            f"加粗过密（每千字 {per_kilo:.1f} 处，超过 {_BOLD_PER_KILO_LIMIT:.0f} 的建议上限），"
            "读起来像 AI 排版；用论述和层次代替大量加粗强调。"
        )

    return issues
