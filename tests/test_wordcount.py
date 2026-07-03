from __future__ import annotations

from core.wordcount import count_words, strip_markdown


def test_count_words_counts_cjk_per_character() -> None:
    assert count_words("物联网技术与实践") == 8


def test_count_words_counts_western_word_as_one() -> None:
    # CJK「窄带物联」4 + 「与」1 = 5，"NB-IoT" 与 "5G" 各计 1 词
    assert count_words("窄带物联 NB-IoT 与 5G") == 5 + 2


def test_count_words_excludes_code_blocks() -> None:
    md = "核心概念说明。\n\n```python\nprint('hello world this is code')\n```\n\n结束语。"
    # 仅「核心概念说明。」6 字 + 「结束语。」4 字（含句号，均为 CJK 计入）
    assert count_words(md) == len("核心概念说明。") + len("结束语。")


def test_count_words_excludes_inline_code_and_markup() -> None:
    md = "## 标题\n\n**加粗**的 `inline_code` 内容。"
    # 标记 #/**/` 与行内代码不计；标题文字计入，剩「标题加粗的内容。」
    assert count_words(md) == len("标题加粗的内容。")


def test_count_words_keeps_link_text_drops_url() -> None:
    md = "参见[官方文档](https://example.com/very/long/path)说明。"
    # 链接文字「官方文档」计入，URL 不计；剩「参见官方文档说明。」
    assert count_words(md) == len("参见官方文档说明。")


def test_count_words_drops_image_alt_and_url() -> None:
    md = "示意如下：![架构图](img/arch.png)请参考。"
    assert count_words(md) == len("示意如下：请参考。")


def test_strip_markdown_removes_list_and_heading_prefixes() -> None:
    md = "# 一级\n- 列表项甲\n1. 有序项乙"
    stripped = strip_markdown(md)
    assert "#" not in stripped
    assert count_words(md) == len("一级列表项甲有序项乙")


def test_count_words_far_smaller_than_len_for_marked_up_text() -> None:
    md = "# 标题\n\n```py\n" + "x = 1\n" * 50 + "```\n\n正文内容。"
    # len(markdown) 会把 300+ 字符的代码计入；count_words 只认「标题正文内容。」的 CJK
    assert count_words(md) < len(md)
    assert count_words(md) == len("标题正文内容。")
