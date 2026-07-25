"""
RAG 模块 - PDF 参考书籍索引与检索
使用 ChromaDB 作为向量数据库
"""

from __future__ import annotations

import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

import chromadb
from chromadb.config import Settings

from core.log import get_logger
from core.rag_bm25 import BM25Index
from core.rag_chunking import split_text
from core.rag_manifest import (
    build_manifest,
    manifest_file_map,
    manifest_matches,
    manifest_static_matches,
    read_manifest,
    write_manifest,
)
from core.rag_markdown import extract_markdown_sections
from core.rag_pdf import extract_pdf_pages
from core.rag_sources import ReferenceSource, SourceFile, iter_source_files
from core.state import ReferenceChunk

# RRF 融合常数（业界缺省 60）
_RRF_K = 60
# dense / sparse 各自的候选池大小
_CANDIDATE_POOL = 30
_DENSE_PROBE_TIMEOUT_SECONDS = 30.0

logger = get_logger("rag")

# 分块数据结构
_TEXT_KEYS = ("text", "source_file", "chapter_or_section", "chunk_index")

_SLUG_RE = re.compile(r"[^0-9A-Za-z_]+")
_CHROMA_CLIENT_INIT_LOCK = threading.RLock()


def _slug(rel: str) -> str:
    """将相对路径转为可用于 chunk_id 的 slug（保留唯一性，仅规整分隔符）。"""
    return _SLUG_RE.sub("_", rel).strip("_")


class RAGEngine:
    """
    RAG 引擎：负责 PDF 解析、分块、向量化、检索。

    使用 ChromaDB 作为向量数据库：
    - HNSW 索引，检索 O(log n)
    - 本地持久化，无需外部服务
    - 自动去重（基于 chunk hash）
    """

    def __init__(
        self,
        embed_fn: Callable[[str], list[float]],
        embed_many_fn: Callable[[list[str]], list[list[float]]] | None = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        persist_dir: str = ".chroma",
        bm25_path: str = "",
        reranker: Callable[[str, list[ReferenceChunk], int], list[ReferenceChunk]] | None = None,
        contextualizer: Callable[[str, str, str], str] | None = None,
        embed_model: str = "",
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap 不能小于 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")
        self.embed_fn = embed_fn
        self.embed_many_fn = embed_many_fn
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._persist_dir = persist_dir
        self._bm25_path = bm25_path
        # 嵌入模型名，纳入 manifest 签名：换模型必须重建索引
        self._embed_model = embed_model
        # rerank 回调（None=不启用）；由上层注入，保持 RAGEngine 与 LLM 解耦
        self._reranker = reranker
        # 分块情境化回调（None=不启用）；入库前对分块补全局上下文
        self._contextualizer = contextualizer

        # 延迟初始化 ChromaDB
        self._client: Any | None = None
        self._collection: Any | None = None
        self._dense_available: bool | None = None
        self._dense_chunk_count = 0
        self._dense_failure_reason = ""
        self._dense_probe_lock = threading.Lock()
        self._sparse_fallback_logged = False
        # BM25 稀疏索引（延迟加载）
        self._bm25: BM25Index | None = None
        self._bm25_loaded = False

    @property
    def collection(self) -> Any:
        if self._collection is None:
            with _CHROMA_CLIENT_INIT_LOCK:
                if self._collection is None:
                    if not self._ensure_dense_available():
                        raise RuntimeError(self._dense_unavailable_message())
                    Path(self._persist_dir).mkdir(parents=True, exist_ok=True)
                    self._client = chromadb.PersistentClient(
                        path=self._persist_dir,
                        settings=Settings(anonymized_telemetry=False),
                    )
                    self._collection = self._client.get_or_create_collection(
                        name="books",
                        metadata={"hnsw:space": "cosine"},
                    )
                    self._dense_chunk_count = cast("int", self._collection.count())
                    logger.info("ChromaDB 初始化: %s (已有 %d 条记录)", self._persist_dir, self._dense_chunk_count)
        return self._collection

    def _ensure_dense_available(self) -> bool:
        """在父进程接触 Chroma 前，以隔离进程探测 native 存储健康度。"""
        if self._dense_available is not None:
            return self._dense_available
        with self._dense_probe_lock:
            if self._dense_available is not None:
                return self._dense_available
            available, count, reason = self._probe_dense_index()
            self._dense_available = available
            self._dense_chunk_count = count
            self._dense_failure_reason = reason
            if not available:
                logger.error("ChromaDB 健康探测失败，禁止父进程加载原生索引: %s", reason)
            return available

    def _probe_dense_index(self) -> tuple[bool, int, str]:
        """运行隔离探针；子进程即使 segfault 也只返回失败状态。"""
        persist_dir = Path(self._persist_dir)
        if not (persist_dir / "chroma.sqlite3").exists():
            return True, 0, ""
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "core.chroma_probe", str(persist_dir)],
                cwd=str(Path(__file__).resolve().parent.parent),
                capture_output=True,
                text=True,
                timeout=_DENSE_PROBE_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, 0, f"探针执行失败: {exc}"
        if completed.returncode != 0:
            if completed.returncode < 0:
                return False, 0, f"native signal {-completed.returncode}"
            detail = completed.stderr.strip().splitlines()
            return False, 0, detail[-1][:500] if detail else f"probe exit {completed.returncode}"
        output = completed.stdout.strip().splitlines()
        try:
            count = int(output[-1])
        except (IndexError, ValueError):
            return False, 0, "探针未返回有效 chunk count"
        return True, count, ""

    def _dense_unavailable_message(self) -> str:
        reason = self._dense_failure_reason or "unknown"
        return f"ChromaDB 原生索引不可用: {reason}。请重建向量索引，hybrid 检索可自动降级到 BM25。"

    def get_status(self) -> dict[str, object]:
        """返回 RAG 索引健康状态。"""
        available = self._ensure_dense_available()
        count = self._dense_chunk_count if available else 0
        return {
            "persist_dir": self._persist_dir,
            "collection": "books",
            "chunk_count": count,
            "healthy": available and count > 0,
            "dense_available": available,
            "dense_failure_reason": self._dense_failure_reason,
        }

    def reset_index(self) -> None:
        """清空并重建 Chroma collection。"""
        _ = self.collection
        if self._client is not None:
            self._client.delete_collection(name="books")
            self._collection = self._client.get_or_create_collection(
                name="books",
                metadata={"hnsw:space": "cosine"},
            )
            self._dense_available = True
            self._dense_chunk_count = 0
            self._dense_failure_reason = ""

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self.embed_many_fn is not None:
            return self.embed_many_fn(texts)
        return [self.embed_fn(text) for text in texts]

    def _extract_blocks(self, source_file: SourceFile) -> list[dict[str, Any]]:
        """按扩展名分派提取器，归一为 {unit, text, section} 块列表。"""
        path = str(source_file.abs_path)
        if source_file.suffix == ".pdf":
            return [
                {"unit": int(page["page"]), "text": page["text"], "section": page["section"]}
                for page in extract_pdf_pages(path)
            ]
        # .md / .markdown
        return [dict(section) for section in extract_markdown_sections(path)]

    def _build_chunks(
        self,
        source_files: Sequence[SourceFile],
        *,
        contextualize: bool = True,
    ) -> tuple[list[str], list[str], list[str], list[dict[str, Any]]]:
        """解析来源文件并构建 Chroma 所需的 ids/documents/embedding_texts/metadatas。"""
        all_ids: list[str] = []
        all_doc_texts: list[str] = []
        all_embed_texts: list[str] = []
        all_metadatas: list[dict[str, Any]] = []

        for source_file in source_files:
            logger.info("处理: %s/%s", source_file.label, source_file.rel)
            blocks = self._extract_blocks(source_file)
            for block in blocks:
                text_parts = split_text(str(block["text"]), self.chunk_size, self.chunk_overlap)
                for ci, chunk_text in enumerate(text_parts):
                    if len(chunk_text) < 50:
                        continue
                    unit = int(block["unit"])
                    embed_text = chunk_text
                    if contextualize and self._contextualizer is not None:
                        embed_text = self._contextualizer(source_file.rel, str(block["section"]), chunk_text)
                    all_ids.append(f"{source_file.label}__{_slug(source_file.rel)}__u{unit}_c{ci}")
                    all_doc_texts.append(chunk_text)
                    all_embed_texts.append(embed_text)
                    all_metadatas.append(
                        {
                            "source_file": self._source_path(source_file),
                            "chapter_or_section": str(block["section"]),
                            "chunk_index": ci,
                            "label": source_file.label,
                            "categories": list(source_file.categories),
                            "doc_type": source_file.doc_type,
                            "language": source_file.language,
                        }
                    )
        return all_ids, all_doc_texts, all_embed_texts, all_metadatas

    def _add_chunks(
        self,
        all_ids: list[str],
        all_doc_texts: list[str],
        all_embed_texts: list[str],
        all_metadatas: list[dict[str, Any]],
        start_index: int = 0,
    ) -> None:
        """批量写入 ChromaDB。"""
        batch_size = 500
        for i in range(start_index, len(all_ids), batch_size):
            batch_ids = all_ids[i : i + batch_size]
            batch_docs = all_doc_texts[i : i + batch_size]
            batch_metas = all_metadatas[i : i + batch_size]
            batch_embeddings = self._embed_texts(all_embed_texts[i : i + batch_size])

            self.collection.add(
                ids=batch_ids,
                documents=batch_docs,
                embeddings=batch_embeddings,
                metadatas=batch_metas,
            )
            self._dense_chunk_count += len(batch_ids)
            logger.info("已索引 %d/%d", min(i + batch_size, len(all_ids)), len(all_ids))

    def _delete_source_paths(self, source_paths: Sequence[str]) -> int:
        """删除指定 source_file 对应的所有分块，返回删除数量。"""
        deleted = 0
        for source_path in source_paths:
            existing = self.collection.get(where={"source_file": source_path})
            ids = list(existing.get("ids") or [])
            if not ids:
                continue
            self.collection.delete(ids=ids)
            deleted += len(ids)
            self._dense_chunk_count = max(0, self._dense_chunk_count - len(ids))
        return deleted

    def _rebuild_bm25_from_collection(self) -> None:
        """从 Chroma 当前内容重建 BM25；用于增量更新后保持稀疏索引一致。"""
        if not self._bm25_path:
            return
        logger.info("重建 BM25 稀疏索引...")
        data = self.collection.get(include=["documents", "metadatas"])
        ids = list(data.get("ids") or [])
        docs = [str(value) for value in data.get("documents") or []]
        metas = [dict(value) for value in data.get("metadatas") or []]
        self._bm25 = BM25Index.build(ids, docs, metas)
        self._bm25.save(self._bm25_path)
        self._bm25_loaded = True
        logger.info("BM25 索引完成: %d 个分块", len(ids))

    @staticmethod
    def _source_path(source_file: SourceFile) -> str:
        return f"{source_file.label}/{source_file.rel}"

    def index_books(self, sources: Sequence[ReferenceSource], index_path: str = "", force_rebuild: bool = False) -> int:
        """
        索引所有参考来源下的受支持文件（PDF + Markdown）。

        Args:
            sources: 参考来源目录列表
            index_path: 索引输入签名文件路径

        Returns:
            分块总数
        """
        manifest = build_manifest(
            sources,
            self.chunk_size,
            self.chunk_overlap,
            embed_model=self._embed_model,
            contextualize=self._contextualizer is not None,
        )

        count = cast("int", self.collection.count())
        if count > 0 and not force_rebuild and manifest_matches(index_path, manifest):
            logger.info("已有索引: %d 条记录，跳过构建", count)
            return count

        partial_index_path = f"{index_path}.partial" if index_path else ""
        resume_partial = count > 0 and not force_rebuild and manifest_matches(partial_index_path, manifest)
        source_files = iter_source_files(sources)
        logger.info("发现 %d 个参考文件，开始索引...", len(source_files))
        if not source_files:
            raise RuntimeError("未发现可索引的参考文件，请检查 references.sources 配置。")

        if resume_partial:
            logger.info("检测到未完成参考索引，续写已有 %d 条记录", count)
            return self._index_full(source_files, manifest, index_path, partial_index_path, start_count=count)

        old_manifest = read_manifest(index_path)
        if count > 0 and not force_rebuild and manifest_static_matches(old_manifest, manifest):
            return self._index_incremental(source_files, old_manifest, manifest, index_path)

        if count > 0:
            logger.info("参考索引配置已变化或要求重建，清空旧索引: %d 条记录", count)
            self.reset_index()
        return self._index_full(source_files, manifest, index_path, partial_index_path, start_count=0)

    def _index_full(
        self,
        source_files: Sequence[SourceFile],
        manifest: dict[str, object],
        index_path: str,
        partial_index_path: str,
        start_count: int = 0,
    ) -> int:
        """全量索引；start_count > 0 时用于中断续写。"""
        all_ids, all_doc_texts, all_embed_texts, all_metadatas = self._build_chunks(source_files)
        if not all_ids:
            raise RuntimeError("参考索引未提取到有效分块，请检查源文件内容和 chunk 配置。")

        logger.info("正在索引 %d 个分块到 ChromaDB...", len(all_ids))
        if partial_index_path:
            write_manifest(partial_index_path, manifest)
        self._add_chunks(
            all_ids,
            all_doc_texts,
            all_embed_texts,
            all_metadatas,
            start_index=min(start_count, len(all_ids)),
        )
        logger.info("索引完成: %d 个分块", len(all_ids))

        if self._bm25_path:
            logger.info("构建 BM25 稀疏索引...")
            self._bm25 = BM25Index.build(
                all_ids,
                all_embed_texts,
                all_metadatas,
                payload_documents=all_doc_texts,
            )
            self._bm25.save(self._bm25_path)
            self._bm25_loaded = True
            logger.info("BM25 索引完成: %d 个分块", len(all_ids))

        write_manifest(index_path, manifest)
        if partial_index_path:
            Path(partial_index_path).unlink(missing_ok=True)
        return len(all_ids)

    def _index_incremental(
        self,
        source_files: Sequence[SourceFile],
        old_manifest: dict[str, object] | None,
        manifest: dict[str, object],
        index_path: str,
    ) -> int:
        """文件级增量索引：只重建新增/变更/删除文件对应的分块。"""
        if self._contextualizer is not None:
            logger.info("已启用 contextualize，文件变化需全量重建以保持 BM25 检索文本一致")
            self.reset_index()
            return self._index_full(source_files, manifest, index_path, f"{index_path}.partial" if index_path else "")

        old_files = manifest_file_map(old_manifest)
        new_files = manifest_file_map(manifest)
        changed_keys = sorted(key for key, value in new_files.items() if old_files.get(key) != value)
        removed_keys = sorted(key for key in old_files if key not in new_files)
        if not changed_keys and not removed_keys:
            logger.info("索引签名不一致但文件签名未变化，执行全量重建以避免复用旧格式索引")
            self.reset_index()
            return self._index_full(source_files, manifest, index_path, f"{index_path}.partial" if index_path else "")

        by_key = {(source_file.label, source_file.rel): source_file for source_file in source_files}
        changed_files = [by_key[key] for key in changed_keys if key in by_key]
        delete_paths = [f"{source}/{rel}" for source, rel in [*changed_keys, *removed_keys]]
        deleted = self._delete_source_paths(delete_paths)
        logger.info(
            "增量更新参考索引: 新增/变更 %d 个文件，删除 %d 个文件，移除 %d 个旧分块",
            len(changed_files),
            len(removed_keys),
            deleted,
        )

        if changed_files:
            all_ids, all_doc_texts, all_embed_texts, all_metadatas = self._build_chunks(changed_files)
            if all_ids:
                logger.info("正在增量索引 %d 个分块到 ChromaDB...", len(all_ids))
                self._add_chunks(all_ids, all_doc_texts, all_embed_texts, all_metadatas)

        self._rebuild_bm25_from_collection()
        write_manifest(index_path, manifest)
        count = cast("int", self.collection.count())
        logger.info("增量索引完成: 当前 %d 个分块", count)
        return count

    def _get_bm25(self) -> BM25Index | None:
        """延迟加载 BM25 索引（内存重建，无需重分词）。"""
        if not self._bm25_loaded:
            self._bm25 = BM25Index.load(self._bm25_path) if self._bm25_path else None
            self._bm25_loaded = True
        return self._bm25

    def rebuild_sparse_index(self, sources: Sequence[ReferenceSource]) -> int:
        """仅从本地参考资料重建 BM25，不初始化 Chroma 或调用 embedding。"""
        if not self._bm25_path:
            raise RuntimeError("sparse-only 构建需要配置 bm25_path。")
        source_files = iter_source_files(sources)
        if not source_files:
            raise RuntimeError("未发现可索引的参考文件，请检查 references.sources 配置。")
        ids, documents, _embedding_texts, metadatas = self._build_chunks(source_files, contextualize=False)
        if not ids:
            raise RuntimeError("稀疏索引未提取到有效分块，请检查源文件内容和 chunk 配置。")
        self._bm25 = BM25Index.build(ids, documents, metadatas)
        self._bm25.save(self._bm25_path)
        self._bm25_loaded = True
        logger.info("BM25 稀疏索引独立重建完成: %d 个分块", len(ids))
        return len(ids)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        *,
        categories: Sequence[str] | None = None,
        doc_type: str | None = None,
        language: str | None = None,
        hybrid: bool = True,
    ) -> list[ReferenceChunk]:
        """检索相关参考段落。

        - categories/doc_type/language: 可选的 metadata 过滤（categories 为多标签，任一命中即可）。
        - hybrid: True 时 dense + BM25 双路 RRF 融合；False 时显式使用纯向量。
        """
        if not self._ensure_dense_available():
            if not hybrid:
                raise RuntimeError(self._dense_unavailable_message())
            if not self._sparse_fallback_logged:
                logger.warning("ChromaDB 不可用，hybrid 检索已自动降级到 BM25: %s", self._dense_failure_reason)
                self._sparse_fallback_logged = True
            return self.retrieve_sparse(
                query,
                top_k=top_k,
                categories=categories,
                doc_type=doc_type,
                language=language,
            )
        if self._dense_chunk_count == 0:
            if hybrid and self._bm25_path:
                logger.warning("ChromaDB 索引为空，hybrid 检索降级到 BM25")
                return self.retrieve_sparse(
                    query,
                    top_k=top_k,
                    categories=categories,
                    doc_type=doc_type,
                    language=language,
                )
            logger.warning("RAG 向量索引为空，无法执行 dense 检索")
            return []

        where = self._build_where(categories, doc_type, language)
        dense = self._dense_search(query, where)
        if not hybrid:
            candidates = [
                self._to_chunk(payload, score=1.0 / (_RRF_K + rank)) for rank, (_, payload) in enumerate(dense, 1)
            ]
        else:
            if not self._bm25_path:
                raise RuntimeError("hybrid 检索需要配置 bm25_path；如需纯向量检索请显式传入 hybrid=False。")
            bm25 = self._get_bm25()
            if bm25 is None:
                raise RuntimeError("BM25 索引不存在，无法执行 hybrid 检索；请重建 RAG 索引。")
            sparse = bm25.search(query, top_n=_CANDIDATE_POOL, where=where)
            candidates = self._rrf_merge(dense, sparse)

        # 可选 rerank：从更宽的候选里精排到 top_k；未启用则直接截断
        if self._reranker is not None and len(candidates) > 1:
            return self._reranker(query, candidates, top_k)
        return candidates[:top_k]

    def retrieve_sparse(
        self,
        query: str,
        top_k: int = 5,
        *,
        categories: Sequence[str] | None = None,
        doc_type: str | None = None,
        language: str | None = None,
    ) -> list[ReferenceChunk]:
        """仅使用本地 BM25 检索，不触发远程 embedding。"""
        if not self._bm25_path:
            raise RuntimeError("sparse 检索需要配置 bm25_path；请重建 RAG 索引。")
        bm25 = self._get_bm25()
        if bm25 is None:
            raise RuntimeError("BM25 索引不存在，无法执行 sparse 检索；请重建 RAG 索引。")

        where = self._build_where(categories, doc_type, language)
        sparse = bm25.search(query, top_n=max(top_k, _CANDIDATE_POOL), where=where)
        chunks: list[ReferenceChunk] = []
        for cid, score in sparse:
            stored = bm25.get_payload(cid)
            if stored is None:
                continue
            document, metadata = stored
            payload = {
                "source_file": str(metadata.get("source_file", "")),
                "chapter_or_section": str(metadata.get("chapter_or_section", "")),
                "text": document,
                "label": str(metadata.get("label", "")),
            }
            chunks.append(self._to_chunk(payload, score=score))
            if len(chunks) >= top_k:
                break
        return chunks

    def _build_where(
        self, categories: Sequence[str] | None, doc_type: str | None, language: str | None
    ) -> dict[str, Any] | None:
        """组装 ChromaDB where 过滤条件；全空返回 None（全局检索）。"""
        clauses: list[dict[str, Any]] = []
        if categories:
            cat_list = list(categories)
            if len(cat_list) == 1:
                clauses.append({"categories": {"$contains": cat_list[0]}})
            else:
                clauses.append({"$or": [{"categories": {"$contains": c}} for c in cat_list]})
        if doc_type:
            clauses.append({"doc_type": doc_type})
        if language:
            clauses.append({"language": language})
        if not clauses:
            return None
        return clauses[0] if len(clauses) == 1 else {"$and": clauses}

    def _dense_search(self, query: str, where: dict[str, Any] | None) -> list[tuple[str, dict[str, Any]]]:
        """向量检索，返回 [(chunk_id, {source_file, chapter_or_section, text, similarity})]，按相关性有序。"""
        results = self.collection.query(
            query_embeddings=[self.embed_fn(query)],
            n_results=_CANDIDATE_POOL,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        out: list[tuple[str, dict[str, Any]]] = []
        if results and results["ids"] and results["documents"]:
            for cid, doc, meta, dist in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
                strict=True,
            ):
                m = cast("dict[str, Any]", meta)
                out.append(
                    (
                        str(cid),
                        {
                            "source_file": str(m.get("source_file", "")),
                            "chapter_or_section": str(m.get("chapter_or_section", "")),
                            "text": str(doc),
                            "similarity": 1.0 - float(dist),
                            "label": str(m.get("label", "")),
                        },
                    )
                )
        return out

    def _rrf_merge(
        self,
        dense: list[tuple[str, dict[str, Any]]],
        sparse: list[tuple[str, float]],
    ) -> list[ReferenceChunk]:
        """RRF 融合 dense + sparse 两路排名，按 chunk_id 去重，返回完整有序候选。"""
        payloads = {cid: payload for cid, payload in dense}
        scores: dict[str, float] = {}
        for rank, (cid, _) in enumerate(dense, 1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (_RRF_K + rank)
        for rank, (cid, _) in enumerate(sparse, 1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (_RRF_K + rank)
            # sparse 命中但 dense 未覆盖时回取正文；取回失败则不入库，payloads 恒为非空 dict
            if cid not in payloads:
                payload = self._fetch_payload(cid)
                if payload is not None:
                    payloads[cid] = payload

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        chunks: list[ReferenceChunk] = []
        for cid, score in ranked:
            payload = payloads.get(cid)
            if payload:
                chunks.append(self._to_chunk(payload, score=score))
        logger.debug("混合检索融合: dense=%d sparse=%d → %d 候选", len(dense), len(sparse), len(chunks))
        return chunks

    def _fetch_payload(self, chunk_id: str) -> dict[str, Any] | None:
        """按 id 从 chroma 取回正文与 metadata（sparse 命中但 dense 未覆盖时）。"""
        got = self.collection.get(ids=[chunk_id], include=["documents", "metadatas"])
        if not got or not got["ids"]:
            return None
        m = cast("dict[str, Any]", got["metadatas"][0])
        return {
            "source_file": str(m.get("source_file", "")),
            "chapter_or_section": str(m.get("chapter_or_section", "")),
            "text": str(got["documents"][0]),
            "similarity": 0.0,
            "label": str(m.get("label", "")),
        }

    @staticmethod
    def _to_chunk(payload: dict[str, Any], score: float) -> ReferenceChunk:
        return ReferenceChunk(
            source_file=payload["source_file"],
            chapter_or_section=payload["chapter_or_section"],
            text=payload["text"],
            relevance_score=float(score),
            label=payload.get("label", ""),
        )
