from __future__ import annotations

from typing import Any

from core.originality import char_ngram_overlap, split_paragraphs
from core.quality_rules import check_originality
from core.state import ChapterContent, QualitySettings, ReferenceChunk

_PARA = "物联网通过传感器采集数据并上传到云端平台进行统一处理、分析与决策，形成完整闭环。"


class _StubRAG:
    """返回固定命中并记录检索次数的假 RAG。"""

    def __init__(self, chunks: list[ReferenceChunk]) -> None:
        self._chunks = chunks
        self.calls = 0

    def retrieve_sparse(self, query: str, top_k: int = 3, *, categories: Any = None) -> list[ReferenceChunk]:
        self.calls += 1
        return self._chunks


def _settings(**overrides: Any) -> QualitySettings:
    base: dict[str, Any] = {
        "originality_check_enabled": True,
        "originality_max_overlap": 0.35,
        "originality_ngram": 5,
        "originality_min_paragraph_chars": 10,
    }
    base.update(overrides)
    return QualitySettings(**base)


def _content(markdown: str = _PARA) -> ChapterContent:
    return ChapterContent(chapter_id=1, title="测试章", markdown=markdown)


# ---- char_ngram_overlap ----


def test_overlap_identical() -> None:
    assert char_ngram_overlap(_PARA, _PARA) == 1.0


def test_overlap_unrelated() -> None:
    assert char_ngram_overlap(_PARA, "今天天气晴朗适合外出散步和买菜做饭") < 0.05


def test_overlap_partial_in_range() -> None:
    # 前半照搬、后半自写 → 重叠率落在中间区间
    candidate = "物联网通过传感器采集数据并上传到云端平台，随后我用自研调度器做了批处理。"
    overlap = char_ngram_overlap(candidate, _PARA)
    assert 0.2 < overlap < 0.9


def test_overlap_empty() -> None:
    assert char_ngram_overlap("", _PARA) == 0.0


# ---- split_paragraphs ----


def test_split_skips_headings_and_tables() -> None:
    md = "# 标题\n\n正文第一段。\n\n| 表 | 头 |\n\n正文第二段。\n\n```py\ncode\n```"
    paras = split_paragraphs(md)
    assert paras == ["正文第一段。", "正文第二段。"]


# ---- check_originality ----


def test_books_high_overlap_flags_issue() -> None:
    rag = _StubRAG([ReferenceChunk(source_file="书.pdf", chapter_or_section="x", text=_PARA, label="books")])
    issues = check_originality(rag, _content(), _settings())
    assert [i.code for i in issues] == ["originality.suspected_copy"]
    assert "书.pdf" in issues[0].message


def test_dc3_high_overlap_passes() -> None:
    # 与自有内容（dc3）雷同不算侵权
    rag = _StubRAG([ReferenceChunk(source_file="dc3.md", chapter_or_section="x", text=_PARA, label="dc3")])
    assert check_originality(rag, _content(), _settings()) == []


def test_low_overlap_no_issue() -> None:
    rag = _StubRAG(
        [ReferenceChunk(source_file="书.pdf", chapter_or_section="x", text="完全不相关的一段参考文本内容", label="books")]
    )
    assert check_originality(rag, _content(), _settings()) == []


def test_disabled_skips_retrieval() -> None:
    rag = _StubRAG([ReferenceChunk(source_file="书.pdf", chapter_or_section="x", text=_PARA, label="books")])
    issues = check_originality(rag, _content(), _settings(originality_check_enabled=False))
    assert issues == []
    assert rag.calls == 0  # 关闭时完全不检索


def test_short_paragraph_skipped() -> None:
    rag = _StubRAG([ReferenceChunk(source_file="书.pdf", chapter_or_section="x", text=_PARA, label="books")])
    issues = check_originality(rag, _content("很短"), _settings(originality_min_paragraph_chars=10))
    assert issues == []
    assert rag.calls == 0  # 太短的段落不触发检索
