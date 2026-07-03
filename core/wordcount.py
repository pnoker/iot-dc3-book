"""
中文书稿字数统计

len(markdown) 对中文是字符数，且把 Markdown 标记、代码、空白全计入，与「4000-8000字」
的目标不是同一量纲，会让内容充实度判据失真。此模块先剥离不计入正文字数的元素
（代码块、行内代码、链接/图片语法、标题与强调标记、表格线等），再按
「CJK 字符逐字计数 + 连续西文单词计 1」统计，贴近中文出版语境的「字数」。
"""

from __future__ import annotations

import re

# 代码围栏块（```...``` / ~~~...~~~）：整段不计入正文字数
_FENCE_BLOCK_RE = re.compile(r"(```|~~~).*?\1", re.DOTALL)
# 行内代码 `code`
_INLINE_CODE_RE = re.compile(r"`[^`]*`")
# 图片 ![alt](url) —— 先于链接处理，去掉整体（alt 不计字数）
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
# 链接 [text](url) —— 保留 text，去掉 url 与括号
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
# 行首标记：标题 #、引用 >、列表 - * + 、有序列表 1. （连同其后空白）
_LINE_PREFIX_RE = re.compile(r"^[ \t]*(#{1,6}|>+|[-*+]|\d+\.)[ \t]+", re.MULTILINE)
# 强调/分隔标记与表格线：* _ ~ ` | 以及水平线
_MARKUP_CHARS_RE = re.compile(r"[*_~`|]+")
# CJK 统一表意文字 + 中文标点（逐字计数）
_CJK_RE = re.compile(r"[㐀-鿿　-〿＀-￯]")
# 连续西文单词（字母/数字/连字符），整体计 1 个词
_WESTERN_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-]*")


def strip_markdown(markdown: str) -> str:
    """移除不计入正文字数的 Markdown 元素，返回近似纯文本。"""
    text = _FENCE_BLOCK_RE.sub(" ", markdown)
    text = _IMAGE_RE.sub(" ", text)
    text = _LINK_RE.sub(r"\1", text)
    text = _INLINE_CODE_RE.sub(" ", text)
    text = _LINE_PREFIX_RE.sub("", text)
    text = _MARKUP_CHARS_RE.sub(" ", text)
    return text


def count_words(markdown: str) -> int:
    """统计中文书稿字数：CJK 逐字 + 西文单词各计 1，剥离 Markdown 标记与代码。"""
    text = strip_markdown(markdown)
    cjk = len(_CJK_RE.findall(text))
    western = len(_WESTERN_WORD_RE.findall(_CJK_RE.sub(" ", text)))
    return cjk + western
