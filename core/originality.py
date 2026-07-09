"""原创性检测：把正文按段落切分，与参考原文做字符 n-gram 重叠度比对。

用于出版前的近似抄袭/洗稿检测：正文段落若与某本参考书原文的字符 n-gram
高度重叠，说明只是「贴着原文改」，需要重写。纯确定性算法，不依赖 LLM。
中文用字符 n-gram（而非词 n-gram）以规避分词依赖，对中文更稳。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# 与 quality_rules._check_unsourced_hard_facts 一致的段落切法：空行分段，
# 跳过标题、表格、代码块/规格块围栏行，避免把结构化内容误判为抄袭。
_PARAGRAPH_SEP_RE = re.compile(r"\n\s*\n")
_SKIP_PREFIXES = ("#", "|", "```", ">")


@dataclass
class SimilarityHit:
    """一段正文与某个参考来源的相似命中。"""

    paragraph_excerpt: str
    source_file: str
    overlap: float
    matched_excerpt: str


def split_paragraphs(markdown: str) -> list[str]:
    """按自然段落切分正文，跳过标题/表格/代码块围栏等非正文行。"""
    paragraphs: list[str] = []
    for block in _PARAGRAPH_SEP_RE.split(markdown):
        text = block.strip()
        if not text or text.startswith(_SKIP_PREFIXES):
            continue
        paragraphs.append(text)
    return paragraphs


def _char_ngrams(text: str, n: int) -> set[str]:
    """提取字符 n-gram 集合；剥离空白以免排版差异影响重叠计算。"""
    compact = re.sub(r"\s+", "", text)
    if len(compact) < n:
        return {compact} if compact else set()
    return {compact[i : i + n] for i in range(len(compact) - n + 1)}


def char_ngram_overlap(candidate: str, reference: str, n: int = 5) -> float:
    """候选段落被参考原文覆盖的比例：|A∩B| / |A|。

    分母取候选段落自身的 n-gram 数，衡量「这段有多少是照搬自参考原文的」，
    不受参考原文长度影响。返回 0.0~1.0。
    """
    cand_grams = _char_ngrams(candidate, n)
    if not cand_grams:
        return 0.0
    ref_grams = _char_ngrams(reference, n)
    if not ref_grams:
        return 0.0
    return len(cand_grams & ref_grams) / len(cand_grams)
