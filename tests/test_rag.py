from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from core.rag import RAGEngine
from core.rag_bm25 import BM25Index
from core.rag_chunking import split_text
from core.rag_pdf import _page_has_ocr_candidate, extract_pdf_pages
from core.rag_sources import ReferenceSource


def test_chroma_client_initialization_is_serialized_across_engines(tmp_path, monkeypatch) -> None:
    active_calls = 0
    max_active_calls = 0
    call_lock = threading.Lock()

    class FakeCollection:
        def count(self) -> int:
            return 0

    class FakeClient:
        def get_or_create_collection(self, *, name: str, metadata: dict[str, str]) -> FakeCollection:
            assert name == "books"
            assert metadata == {"hnsw:space": "cosine"}
            return FakeCollection()

    def fake_persistent_client(*, path: str, settings: object) -> FakeClient:
        nonlocal active_calls, max_active_calls
        assert path == str(tmp_path / "chroma")
        assert settings is not None
        with call_lock:
            active_calls += 1
            max_active_calls = max(max_active_calls, active_calls)
        time.sleep(0.02)
        with call_lock:
            active_calls -= 1
        return FakeClient()

    monkeypatch.setattr("core.rag.chromadb.PersistentClient", fake_persistent_client)
    engines = [RAGEngine(embed_fn=lambda text: [0.0], persist_dir=str(tmp_path / "chroma")) for _ in range(6)]

    with ThreadPoolExecutor(max_workers=6) as executor:
        list(executor.map(lambda engine: engine.collection, engines))

    assert max_active_calls == 1


def test_index_books_indexes_pdf_and_markdown_with_unique_ids(tmp_path, monkeypatch) -> None:
    # 两个来源：一个含 PDF，一个含 Markdown（含同名 index.md 场景由 label 前缀保证唯一）
    books = tmp_path / "books"
    docs = tmp_path / "docs"
    books.mkdir()
    docs.mkdir()
    (books / "guide.pdf").write_bytes(b"%PDF-1.4 fake")
    (docs / "index.md").write_text(
        "---\ntitle: DC3 架构\n---\n" + "IoT DC3 使用 Spring AI 构建 Agentic Center。" * 5,
        encoding="utf-8",
    )

    def fake_pdf(path: str) -> list[dict[str, object]]:
        return [{"page": 1, "text": "物联网平台通过网关统一接入多协议设备。" * 5, "section": "第一章"}]

    monkeypatch.setattr("core.rag.extract_pdf_pages", fake_pdf)

    engine = RAGEngine(
        embed_fn=lambda text: [float(len(text) % 7), 1.0],
        chunk_size=1000,
        chunk_overlap=100,
        persist_dir=str(tmp_path / "chroma"),
    )
    sources = [
        ReferenceSource(books, "books", categories=("iot",)),
        ReferenceSource(docs, "dc3", categories=("iot", "dc3")),
    ]

    count = engine.index_books(sources, str(tmp_path / "manifest.json"))

    assert count >= 2
    ids = engine.collection.get()["ids"]
    assert len(ids) == len(set(ids))  # chunk_id 全局唯一
    sources_seen = {m["source_file"] for m in engine.collection.get()["metadatas"]}
    assert any(s.startswith("dc3/") for s in sources_seen)  # MD 带 label 前缀
    assert any(s.startswith("books/") for s in sources_seen)  # PDF 带 label 前缀


def test_index_books_writes_category_metadata_and_filters(tmp_path, monkeypatch) -> None:
    docs = tmp_path / "docs"
    (docs / "ai").mkdir(parents=True)
    (docs / "misc").mkdir()
    (docs / "ai" / "a.md").write_text("# AI\n" + "Spring AI 与 Agentic Center 设计。" * 5, encoding="utf-8")
    (docs / "misc" / "b.md").write_text("# 杂项\n" + "一些通用的物联网背景介绍内容。" * 5, encoding="utf-8")

    engine = RAGEngine(
        embed_fn=lambda text: [float(len(text) % 5), 1.0],
        chunk_size=1000,
        chunk_overlap=100,
        persist_dir=str(tmp_path / "chroma"),
    )
    src = ReferenceSource(
        docs,
        "dc3",
        categories=("iot", "dc3"),
        dir_categories=(("ai", ("ai", "agentic")),),
        language="zh",
    )

    engine.index_books([src], str(tmp_path / "manifest.json"))

    # list 型 categories 用 $contains 过滤（$eq/$in 对 list 无效）
    ai_hits = engine.collection.get(where={"categories": {"$contains": "agentic"}})
    assert ai_hits["ids"], "应能按 agentic 标签过滤出 ai 子目录内容"
    for meta in ai_hits["metadatas"]:
        assert "agentic" in meta["categories"]
        assert meta["source_file"].startswith("dc3/ai/")
        assert meta["doc_type"] == "docs"
        assert meta["language"] == "zh"
    # misc 未命中 agentic
    misc_ids = set(engine.collection.get(where={"categories": {"$contains": "agentic"}})["ids"])
    all_ids = set(engine.collection.get()["ids"])
    assert all_ids - misc_ids, "存在非 agentic 的分块"


def test_hybrid_retrieve_recalls_exact_term_via_bm25(tmp_path, monkeypatch) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    # 用固定 embedding：让向量对所有 doc 几乎无区分度，凸显 BM25 的字面召回作用
    (docs / "bg.md").write_text("# 背景\n" + "物联网是万物互联的技术体系与理念。" * 6, encoding="utf-8")
    (docs / "modbus.md").write_text("# 协议\n" + "Modbus 是主从式工业串行通信协议规范。" * 6, encoding="utf-8")

    engine = RAGEngine(
        embed_fn=lambda text: [1.0, 0.0],  # 所有文本同向量 → dense 无区分
        chunk_size=1000,
        chunk_overlap=100,
        persist_dir=str(tmp_path / "chroma"),
        bm25_path=str(tmp_path / "bm25.json"),
    )
    engine.index_books([ReferenceSource(docs, "dc3", categories=("iot", "dc3"))], str(tmp_path / "manifest.json"))

    hybrid_hits = engine.retrieve("Modbus 协议", top_k=2, hybrid=True)
    assert any("Modbus" in c.text for c in hybrid_hits)  # 混合检索召回精确术语
    # BM25 索引在索引期已构建
    assert engine._get_bm25() is not None


def test_sparse_retrieve_uses_bm25_without_embedding(tmp_path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "modbus.md").write_text("# 协议\n" + "Modbus 是主从式工业串行通信协议规范。" * 6, encoding="utf-8")

    embed_calls = {"count": 0}

    def embed(text: str) -> list[float]:
        embed_calls["count"] += 1
        return [1.0, 0.0]

    engine = RAGEngine(
        embed_fn=embed,
        chunk_size=1000,
        chunk_overlap=100,
        persist_dir=str(tmp_path / "chroma"),
        bm25_path=str(tmp_path / "bm25.json"),
    )
    engine.index_books(
        [ReferenceSource(docs, "books", categories=("iot", "protocol"))], str(tmp_path / "manifest.json")
    )
    embed_calls["count"] = 0

    hits = engine.retrieve_sparse("Modbus 协议", top_k=2, categories=["protocol"])

    assert hits
    assert any("Modbus" in hit.text for hit in hits)
    assert embed_calls["count"] == 0


def test_sparse_retrieve_does_not_touch_chroma_collection(tmp_path) -> None:
    bm25_path = tmp_path / "bm25.json"
    BM25Index.build(
        ["chunk-1"],
        ["Modbus 是主从式工业串行通信协议。"],
        [{"source_file": "books/modbus.md", "chapter_or_section": "协议", "label": "books"}],
    ).save(str(bm25_path))
    engine = RAGEngine(
        embed_fn=lambda text: (_ for _ in ()).throw(AssertionError("稀疏检索不应调用 embedding")),
        persist_dir=str(tmp_path / "chroma"),
        bm25_path=str(bm25_path),
    )

    class ExplodingCollection:
        def count(self):
            raise AssertionError("稀疏检索不应访问 Chroma count")

        def get(self, *args, **kwargs):
            raise AssertionError("稀疏检索不应访问 Chroma get")

    engine._collection = ExplodingCollection()

    hits = engine.retrieve_sparse("Modbus", top_k=1)

    assert len(hits) == 1
    assert hits[0].text == "Modbus 是主从式工业串行通信协议。"


def test_hybrid_retrieve_falls_back_to_sparse_when_chroma_is_unhealthy(tmp_path, monkeypatch) -> None:
    bm25_path = tmp_path / "bm25.json"
    BM25Index.build(
        ["chunk-1"],
        ["Modbus 是主从式工业串行通信协议。"],
        [{"source_file": "books/modbus.md", "chapter_or_section": "协议", "label": "books"}],
    ).save(str(bm25_path))
    engine = RAGEngine(
        embed_fn=lambda text: (_ for _ in ()).throw(AssertionError("降级检索不应调用 embedding")),
        persist_dir=str(tmp_path / "chroma"),
        bm25_path=str(bm25_path),
    )
    monkeypatch.setattr(engine, "_probe_dense_index", lambda: (False, 0, "native signal 11"), raising=False)

    hits = engine.retrieve("Modbus", top_k=1)

    assert len(hits) == 1
    assert hits[0].text == "Modbus 是主从式工业串行通信协议。"
    assert engine._collection is None


def test_pure_dense_retrieve_fails_cleanly_when_chroma_is_unhealthy(tmp_path, monkeypatch) -> None:
    engine = RAGEngine(
        embed_fn=lambda text: [1.0, 0.0],
        persist_dir=str(tmp_path / "chroma"),
        bm25_path=str(tmp_path / "bm25.json"),
    )
    monkeypatch.setattr(engine, "_probe_dense_index", lambda: (False, 0, "native signal 11"), raising=False)

    with pytest.raises(RuntimeError, match=r"Chroma.*native signal 11"):
        engine.retrieve("Modbus", top_k=1, hybrid=False)


def test_rebuild_sparse_index_avoids_chroma_and_embedding(tmp_path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "modbus.md").write_text("# 协议\n" + "Modbus 是工业通信协议。" * 8, encoding="utf-8")
    engine = RAGEngine(
        embed_fn=lambda text: (_ for _ in ()).throw(AssertionError("稀疏索引不应调用 embedding")),
        persist_dir=str(tmp_path / "chroma"),
        bm25_path=str(tmp_path / "bm25.json"),
    )

    class ExplodingCollection:
        def count(self):
            raise AssertionError("稀疏索引不应访问 Chroma")

    engine._collection = ExplodingCollection()

    count = engine.rebuild_sparse_index([ReferenceSource(docs, "books", categories=("protocol",))])
    hits = engine.retrieve_sparse("Modbus", top_k=1)

    assert count == 1
    assert hits and "Modbus" in hits[0].text


def test_retrieve_hybrid_false_is_pure_dense(tmp_path, monkeypatch) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("# A\n" + "内容甲。" * 30, encoding="utf-8")

    engine = RAGEngine(
        embed_fn=lambda text: [1.0, 0.0],
        chunk_size=1000,
        chunk_overlap=100,
        persist_dir=str(tmp_path / "chroma"),
        bm25_path=str(tmp_path / "bm25.json"),
    )
    engine.index_books([ReferenceSource(docs, "dc3", categories=("iot", "dc3"))], str(tmp_path / "manifest.json"))

    # hybrid=False 不应触碰 BM25
    monkeypatch.setattr(engine, "_get_bm25", lambda: (_ for _ in ()).throw(AssertionError("不应调用 BM25")))
    hits = engine.retrieve("内容", top_k=3, hybrid=False)
    assert hits  # 纯 dense 仍能返回


def test_retrieve_hybrid_requires_bm25_path(tmp_path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("# A\n" + "内容甲。" * 30, encoding="utf-8")

    engine = RAGEngine(
        embed_fn=lambda text: [1.0, 0.0],
        chunk_size=1000,
        chunk_overlap=100,
        persist_dir=str(tmp_path / "chroma"),
    )
    engine.index_books([ReferenceSource(docs, "dc3", categories=("iot", "dc3"))], str(tmp_path / "manifest.json"))

    with pytest.raises(RuntimeError, match="hybrid 检索需要配置 bm25_path"):
        engine.retrieve("内容", top_k=3, hybrid=True)


def test_retrieve_category_filter_scopes_results(tmp_path) -> None:
    docs = tmp_path / "docs"
    (docs / "ai").mkdir(parents=True)
    (docs / "net").mkdir()
    (docs / "ai" / "a.md").write_text("# AI\n" + "Spring AI Agentic 设计。" * 6, encoding="utf-8")
    (docs / "net" / "b.md").write_text("# 网络\n" + "NB-IoT 低功耗广域网络。" * 6, encoding="utf-8")

    engine = RAGEngine(
        embed_fn=lambda text: [float(len(text) % 3), 1.0],
        chunk_size=1000,
        chunk_overlap=100,
        persist_dir=str(tmp_path / "chroma"),
        bm25_path=str(tmp_path / "bm25.json"),
    )
    src = ReferenceSource(
        docs,
        "dc3",
        categories=("dc3",),
        dir_categories=(("ai", ("ai",)), ("net", ("network",))),
    )
    engine.index_books([src], str(tmp_path / "manifest.json"))

    hits = engine.retrieve("设计", top_k=5, categories=["ai"], hybrid=True)
    assert hits
    for c in hits:
        assert "/ai/" in c.source_file  # 分类过滤只返回 ai 子目录


def test_retrieve_applies_injected_reranker(tmp_path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    for i in range(4):
        (docs / f"d{i}.md").write_text(f"# 章{i}\n" + f"物联网主题内容第{i}段落说明。" * 6, encoding="utf-8")

    seen: dict[str, int] = {}

    def reranker(query, chunks, top_k):
        seen["candidates"] = len(chunks)
        return list(reversed(chunks))[:top_k]  # 逆序取前 top_k

    engine = RAGEngine(
        embed_fn=lambda text: [float(len(text) % 4), 1.0],
        chunk_size=1000,
        chunk_overlap=100,
        persist_dir=str(tmp_path / "chroma"),
        bm25_path=str(tmp_path / "bm25.json"),
        reranker=reranker,
    )
    engine.index_books([ReferenceSource(docs, "dc3", categories=("iot", "dc3"))], str(tmp_path / "manifest.json"))

    hits = engine.retrieve("物联网", top_k=2, hybrid=True)

    assert len(hits) == 2  # rerank 截断到 top_k
    assert seen["candidates"] >= 2  # rerank 收到比 top_k 更宽的候选


def test_index_books_contextualizer_feeds_embedding_not_stored_text(tmp_path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("# 标题\n" + "Modbus 协议正文内容说明。" * 6, encoding="utf-8")

    embedded: list[str] = []

    def contextualizer(source: str, section: str, chunk_text: str) -> str:
        return f"[情境] {section}\n\n{chunk_text}"

    def embed_fn(text: str) -> list[float]:
        embedded.append(text)
        return [1.0, 0.0]

    engine = RAGEngine(
        embed_fn=embed_fn,
        chunk_size=1000,
        chunk_overlap=100,
        persist_dir=str(tmp_path / "chroma"),
        contextualizer=contextualizer,
    )
    engine.index_books([ReferenceSource(docs, "dc3", categories=("iot", "dc3"))], str(tmp_path / "manifest.json"))

    # 存储正文为原文，不含情境前缀（避免污染最终引用事实）
    stored = engine.collection.get(include=["documents"])["documents"]
    assert stored and all(not d.startswith("[情境]") for d in stored)
    # 情境前缀仅进入嵌入输入
    assert embedded and all(t.startswith("[情境]") for t in embedded)


def test_index_books_skips_rebuild_when_manifest_unchanged(tmp_path, monkeypatch) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("# 标题\n" + "内容。" * 30, encoding="utf-8")
    engine = RAGEngine(
        embed_fn=lambda text: [1.0, 0.0],
        chunk_size=1000,
        chunk_overlap=100,
        persist_dir=str(tmp_path / "chroma"),
    )
    sources = [ReferenceSource(docs, "dc3", categories=("iot", "dc3"))]
    manifest = str(tmp_path / "manifest.json")

    first = engine.index_books(sources, manifest)

    calls: list[str] = []
    monkeypatch.setattr(engine, "reset_index", lambda: calls.append("reset"))
    second = engine.index_books(sources, manifest)

    assert first == second
    assert calls == []  # 输入未变，跳过重建


def test_index_books_incrementally_reindexes_changed_file_without_reset(tmp_path, monkeypatch) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("# A\n" + "旧内容说明。" * 20, encoding="utf-8")
    (docs / "b.md").write_text("# B\n" + "保留内容说明。" * 20, encoding="utf-8")
    engine = RAGEngine(
        embed_fn=lambda text: [float(len(text) % 5), 1.0],
        chunk_size=1000,
        chunk_overlap=100,
        persist_dir=str(tmp_path / "chroma"),
    )
    sources = [ReferenceSource(docs, "dc3", categories=("iot", "dc3"))]
    manifest = str(tmp_path / "manifest.json")

    first = engine.index_books(sources, manifest)
    (docs / "a.md").write_text("# A\n" + "新内容说明。" * 25, encoding="utf-8")
    calls: list[str] = []
    monkeypatch.setattr(engine, "reset_index", lambda: calls.append("reset"))

    second = engine.index_books(sources, manifest)

    assert second == first
    assert calls == []
    a_docs = engine.collection.get(where={"source_file": "dc3/a.md"}, include=["documents"])["documents"]
    b_docs = engine.collection.get(where={"source_file": "dc3/b.md"}, include=["documents"])["documents"]
    assert a_docs and all("新内容" in doc for doc in a_docs)
    assert b_docs and all("保留内容" in doc for doc in b_docs)


def test_index_books_incrementally_removes_deleted_file_without_reset(tmp_path, monkeypatch) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("# A\n" + "保留内容说明。" * 20, encoding="utf-8")
    (docs / "b.md").write_text("# B\n" + "删除内容说明。" * 20, encoding="utf-8")
    engine = RAGEngine(
        embed_fn=lambda text: [1.0, 0.0],
        chunk_size=1000,
        chunk_overlap=100,
        persist_dir=str(tmp_path / "chroma"),
    )
    sources = [ReferenceSource(docs, "dc3", categories=("iot", "dc3"))]
    manifest = str(tmp_path / "manifest.json")

    engine.index_books(sources, manifest)
    (docs / "b.md").unlink()
    calls: list[str] = []
    monkeypatch.setattr(engine, "reset_index", lambda: calls.append("reset"))

    count = engine.index_books(sources, manifest)

    assert count == 1
    assert calls == []
    metadatas = engine.collection.get()["metadatas"]
    assert {meta["source_file"] for meta in metadatas} == {"dc3/a.md"}


def test_rag_rejects_overlap_not_smaller_than_chunk_size(tmp_path) -> None:
    with pytest.raises(ValueError, match="chunk_overlap 必须小于 chunk_size"):
        RAGEngine(embed_fn=lambda text: [0.0], chunk_size=100, chunk_overlap=100, persist_dir=str(tmp_path))


def test_rag_status_reports_empty_index_as_unhealthy(tmp_path) -> None:
    engine = RAGEngine(embed_fn=lambda text: [0.0], persist_dir=str(tmp_path))

    status = engine.get_status()

    assert status["chunk_count"] == 0
    assert status["healthy"] is False
    assert status["persist_dir"] == str(tmp_path)


def test_index_books_raises_when_no_effective_chunks(tmp_path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "empty.md").write_text("# 空\n短", encoding="utf-8")
    engine = RAGEngine(
        embed_fn=lambda text: [0.0],
        chunk_size=1000,
        chunk_overlap=100,
        persist_dir=str(tmp_path / "chroma"),
    )

    with pytest.raises(RuntimeError, match="未提取到有效分块"):
        engine.index_books([ReferenceSource(docs, "dc3", categories=("iot",))], str(tmp_path / "manifest.json"))


def test_split_text_uses_langchain_recursive_splitter(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeSplitter:
        def __init__(self, **kwargs: object) -> None:
            calls.append(kwargs)

        def split_text(self, text: str) -> list[str]:
            return [f"split:{text}"]

    monkeypatch.setattr("core.rag_chunking.RecursiveCharacterTextSplitter", FakeSplitter)

    chunks = split_text("物联网平台需要端边云协同。", chunk_size=100, chunk_overlap=20)

    assert chunks == ["split:物联网平台需要端边云协同。"]
    assert calls == [
        {
            "chunk_size": 100,
            "chunk_overlap": 20,
            "separators": ["\n\n", "\n", "。", "；", ".", " ", ""],
            "keep_separator": True,
        }
    ]


def test_extract_pdf_pages_uses_text_extraction_without_ocr_first(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def text_markdown(pdf_path: str, **kwargs: object) -> list[dict[str, object]]:
        calls.append({"pdf_path": pdf_path, **kwargs})
        return [
            {"metadata": {"page": 1}, "text": "# 第一章 总览\n正文"},
            {"metadata": {"page": 2}, "text": "延续正文"},
        ]

    monkeypatch.setattr("core.rag_pdf.pymupdf4llm.to_markdown", text_markdown)

    pages = extract_pdf_pages("book.pdf")

    assert pages == [
        {"page": 1, "text": "# 第一章 总览\n正文", "section": "第一章 总览"},
        {"page": 2, "text": "延续正文", "section": "第一章 总览"},
    ]
    assert calls == [{"pdf_path": "book.pdf", "page_chunks": True, "use_ocr": False}]


def test_extract_pdf_pages_ocr_fallbacks_empty_text_pages_only(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def markdown(pdf_path: str, **kwargs: object) -> list[dict[str, object]]:
        calls.append({"pdf_path": pdf_path, **kwargs})
        if kwargs.get("use_ocr") is False:
            return [
                {"metadata": {"page": 1}, "text": "# 第一章 总览\n正文"},
                {"metadata": {"page": 2}, "text": ""},
            ]
        return [{"metadata": {"page": 2}, "text": "OCR 识别出的图片文字"}]

    monkeypatch.setattr("core.rag_pdf.pymupdf4llm.to_markdown", markdown)
    monkeypatch.setattr("core.rag_pdf._filter_ocr_candidate_page_indexes", lambda pdf_path, page_indexes: page_indexes)

    pages = extract_pdf_pages("book.pdf")

    assert pages == [
        {"page": 1, "text": "# 第一章 总览\n正文", "section": "第一章 总览"},
        {"page": 2, "text": "OCR 识别出的图片文字", "section": "第一章 总览"},
    ]
    assert calls == [
        {"pdf_path": "book.pdf", "page_chunks": True, "use_ocr": False},
        {
            "pdf_path": "book.pdf",
            "page_chunks": True,
            "pages": [1],
            "use_ocr": True,
            "force_ocr": True,
        },
    ]


def test_extract_pdf_pages_skips_ocr_for_pages_with_only_tiny_images(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def markdown(pdf_path: str, **kwargs: object) -> list[dict[str, object]]:
        calls.append({"pdf_path": pdf_path, **kwargs})
        return [
            {"metadata": {"page": 1}, "text": "# 第一章 总览\n正文"},
            {"metadata": {"page": 2}, "text": ""},
        ]

    monkeypatch.setattr("core.rag_pdf.pymupdf4llm.to_markdown", markdown)
    monkeypatch.setattr("core.rag_pdf._filter_ocr_candidate_page_indexes", lambda pdf_path, page_indexes: [])

    pages = extract_pdf_pages("book.pdf")

    assert pages == [{"page": 1, "text": "# 第一章 总览\n正文", "section": "第一章 总览"}]
    assert calls == [{"pdf_path": "book.pdf", "page_chunks": True, "use_ocr": False}]


def test_page_has_ocr_candidate_rejects_tiny_images(monkeypatch) -> None:
    monkeypatch.setattr("core.rag_pdf.pymupdf.open", lambda pdf_path: FakePdfDocument(tiny_image_blocks()))

    assert _page_has_ocr_candidate("book.pdf", 0) is False


def test_page_has_ocr_candidate_accepts_large_images(monkeypatch) -> None:
    monkeypatch.setattr("core.rag_pdf.pymupdf.open", lambda pdf_path: FakePdfDocument(large_image_blocks()))

    assert _page_has_ocr_candidate("book.pdf", 0) is True


def test_extract_pdf_pages_propagates_wrapped_keyboard_interrupt(monkeypatch) -> None:
    def interrupted_markdown(pdf_path: str, **kwargs: object) -> object:
        raise RuntimeError("Director error: <class 'KeyboardInterrupt'>")

    monkeypatch.setattr("core.rag_pdf.pymupdf4llm.to_markdown", interrupted_markdown)

    with pytest.raises(KeyboardInterrupt):
        extract_pdf_pages("book.pdf")


class FakeRect:
    width = 612
    height = 792


class FakePdfPage:
    rect = FakeRect()

    def __init__(self, blocks: list[dict[str, object]]) -> None:
        self._blocks = blocks

    def get_text(self, kind: str, **kwargs: object) -> dict[str, object]:
        assert kind == "dict"
        return {"blocks": self._blocks}


class FakePdfDocument:
    page_count = 1

    def __init__(self, blocks: list[dict[str, object]]) -> None:
        self._blocks = blocks

    def load_page(self, page_index: int) -> FakePdfPage:
        assert page_index == 0
        return FakePdfPage(self._blocks)

    def close(self) -> None:
        pass


def tiny_image_blocks() -> list[dict[str, object]]:
    return [{"type": 1, "bbox": (10, 10, 12, 46), "width": 2, "height": 36}]


def large_image_blocks() -> list[dict[str, object]]:
    return [{"type": 1, "bbox": (40, 60, 520, 700), "width": 1600, "height": 2200}]
