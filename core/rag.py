"""
RAG 模块 - PDF 参考书籍索引与检索
使用 ChromaDB 作为向量数据库
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable

import chromadb
from chromadb.config import Settings

from core.log import get_logger
from core.rag_chunking import split_text
from core.rag_manifest import build_manifest, manifest_matches, write_manifest
from core.rag_pdf import extract_pdf_pages
from core.state import ReferenceChunk

logger = get_logger("rag")

# 分块数据结构
_TEXT_KEYS = ("text", "source_file", "chapter_or_section", "chunk_index")


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

        # 延迟初始化 ChromaDB
        self._client: Any | None = None
        self._collection: Any | None = None

    @property
    def collection(self) -> Any:
        if self._collection is None:
            Path(self._persist_dir).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=self._persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name="books",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB 初始化: %s (已有 %d 条记录)", self._persist_dir, self._collection.count())
        return self._collection

    def get_status(self) -> dict[str, object]:
        """返回 RAG 索引健康状态。"""
        count = cast("int", self.collection.count())
        return {
            "persist_dir": self._persist_dir,
            "collection": "books",
            "chunk_count": count,
            "healthy": count > 0,
        }

    def reset_index(self) -> None:
        """清空并重建 Chroma collection。"""
        _ = self.collection
        if self._client is not None:
            try:
                self._client.delete_collection(name="books")
            except Exception:
                logger.debug("删除旧 collection 失败或不存在", exc_info=True)
            self._collection = self._client.get_or_create_collection(
                name="books",
                metadata={"hnsw:space": "cosine"},
            )

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self.embed_many_fn is not None:
            return self.embed_many_fn(texts)
        return [self.embed_fn(text) for text in texts]

    def index_books(self, books_dir: str, index_path: str = "", force_rebuild: bool = False) -> int:
        """
        索引目录下所有 PDF 书籍。

        Args:
            books_dir: PDF 书籍目录
            index_path: 索引输入签名文件路径

        Returns:
            分块总数
        """
        manifest = build_manifest(books_dir, self.chunk_size, self.chunk_overlap)

        # 如果已有数据且输入未变化，跳过
        count = cast("int", self.collection.count())
        if count > 0 and not force_rebuild and manifest_matches(index_path, manifest):
            logger.info("已有索引: %d 条记录，跳过构建", count)
            return count

        if count > 0:
            logger.info("参考书索引已过期或要求重建，清空旧索引: %d 条记录", count)
            self.reset_index()

        books_path = Path(books_dir)
        if not books_path.exists():
            logger.error("参考书籍目录不存在: %s", books_dir)
            return 0

        pdf_files = sorted(books_path.rglob("*.pdf"))
        logger.info("发现 %d 本 PDF 书籍，开始索引...", len(pdf_files))

        # 收集所有分块
        all_ids: list[str] = []
        all_texts: list[str] = []
        all_metadatas: list[dict[str, str | int]] = []

        for pdf_file in pdf_files:
            logger.info("处理: %s", pdf_file.name)
            try:
                pages = extract_pdf_pages(str(pdf_file))
                for page_info in pages:
                    text_parts = split_text(str(page_info["text"]), self.chunk_size, self.chunk_overlap)
                    for ci, chunk_text in enumerate(text_parts):
                        if len(chunk_text) < 50:
                            continue
                        page_number = int(page_info["page"])
                        chunk_id = f"{pdf_file.stem}_p{page_number}_c{ci}"
                        all_ids.append(chunk_id)
                        all_texts.append(chunk_text)
                        all_metadatas.append(
                            {
                                "source_file": pdf_file.name,
                                "chapter_or_section": str(page_info["section"]),
                                "chunk_index": ci,
                            }
                        )
            except Exception:
                logger.exception("跳过 %s", pdf_file.name)

        if not all_ids:
            logger.warning("没有提取到有效分块")
            return 0

        # 批量写入 ChromaDB（带自定义 embedding 函数）
        logger.info("正在索引 %d 个分块到 ChromaDB...", len(all_ids))
        batch_size = 100
        for i in range(0, len(all_ids), batch_size):
            batch_ids = all_ids[i : i + batch_size]
            batch_texts = all_texts[i : i + batch_size]
            batch_metas = all_metadatas[i : i + batch_size]
            batch_embeddings = self._embed_texts(batch_texts)

            self.collection.add(
                ids=batch_ids,
                documents=batch_texts,
                embeddings=batch_embeddings,
                metadatas=batch_metas,
            )
            logger.info("已索引 %d/%d", min(i + batch_size, len(all_ids)), len(all_ids))

        logger.info("索引完成: %d 个分块", len(all_ids))
        write_manifest(index_path, manifest)
        return len(all_ids)

    def retrieve(self, query: str, top_k: int = 5) -> list[ReferenceChunk]:
        """根据查询检索相关参考段落"""
        if self.collection.count() == 0:
            logger.warning("RAG 索引为空，无法检索")
            return []

        query_embedding = self.embed_fn(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        chunks: list[ReferenceChunk] = []
        if results and results["documents"] and results["metadatas"] and results["distances"]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
                strict=True,
            ):
                # ChromaDB cosine distance: 0 = identical, 2 = opposite
                similarity = 1.0 - dist
                chunks.append(
                    ReferenceChunk(
                        source_file=str(cast("dict[str, Any]", meta).get("source_file", "")),
                        chapter_or_section=str(cast("dict[str, Any]", meta).get("chapter_or_section", "")),
                        text=str(doc),
                        relevance_score=float(similarity),
                    )
                )

        logger.debug("检索 '%s': 返回 %d 个结果", query[:30], len(chunks))
        return chunks
