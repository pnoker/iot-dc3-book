from __future__ import annotations

from core.rag_bm25 import BM25Index, tokenize


def test_tokenize_splits_chinese_and_keeps_ascii_terms() -> None:
    tokens = tokenize("使用 Modbus 协议接入 PLC 设备")

    # 中文被切词、英文技术术语保留（小写）
    assert "modbus" in tokens
    assert "plc" in tokens
    assert "协议" in tokens


def test_bm25_search_ranks_exact_term_first() -> None:
    ids = ["a", "b", "c"]
    docs = [
        "本章介绍通用的物联网背景知识。",
        "Modbus 是一种主从式串行通信协议，广泛用于工业设备。",
        "边缘计算把算力下沉到网络边缘。",
    ]
    metas = [{"label": "x"}, {"label": "x"}, {"label": "x"}]
    idx = BM25Index.build(ids, docs, metas)

    hits = idx.search("Modbus 协议", top_n=3)

    assert hits[0][0] == "b"  # 精确术语命中排第一


def test_bm25_search_applies_where_filter() -> None:
    ids = ["a", "b"]
    docs = ["Spring AI 工具调用", "Spring AI 工具调用"]
    metas = [{"categories": ["ai", "dc3"]}, {"categories": ["network"]}]
    idx = BM25Index.build(ids, docs, metas)

    hits = idx.search("Spring AI", top_n=5, where={"categories": {"$contains": "ai"}})

    assert [cid for cid, _ in hits] == ["a"]  # 只返回含 ai 标签的


def test_bm25_save_load_roundtrip_without_retokenize(tmp_path, monkeypatch) -> None:
    ids = ["a"]
    docs = ["Modbus 协议接入"]
    metas = [{"label": "x"}]
    idx = BM25Index.build(ids, docs, metas)
    path = str(tmp_path / "bm25.json")
    idx.save(path)

    # 加载路径不应再调用分词（token 已落盘）
    import core.rag_bm25 as m

    calls: list[str] = []
    monkeypatch.setattr(m, "tokenize", lambda t: calls.append(t) or [])  # type: ignore[func-returns-value]
    loaded = BM25Index.load(path)

    assert loaded is not None
    assert calls == []  # 加载未触发重分词


def test_bm25_load_missing_returns_none(tmp_path) -> None:
    assert BM25Index.load(str(tmp_path / "nope.json")) is None
