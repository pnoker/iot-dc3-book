"""
BM25 稀疏检索索引

ChromaDB 本地版无可用的原生 hybrid，稀疏检索在应用层用 rank_bm25 实现。
索引落盘时持久化「分词后的 token + id + 过滤用 metadata」而非模型本身——
分词是唯一重活，存 token 即可秒级重建 BM25Okapi。语料与 ChromaDB 同源，防漂移。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import jieba
from rank_bm25 import BM25Okapi

from core.log import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = get_logger("rag")
BM25_FORMAT_VERSION = 2

# 切 ASCII 词、数字、下划线连缀（补 jieba 对英文技术术语的切分）
_ASCII_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")

# jieba 初始化日志噪音大，静音
jieba.setLogLevel("ERROR")


def tokenize(text: str) -> list[str]:
    """中英混合分词：jieba 切中文词 + 正则补 ASCII/数字 token，统一小写。"""
    tokens = [tok.strip().lower() for tok in jieba.lcut(text) if tok.strip()]
    ascii_tokens = [m.group(0).lower() for m in _ASCII_TOKEN_RE.finditer(text)]
    return tokens + ascii_tokens


class BM25Index:
    """内存 BM25 索引，支持落盘/加载与带 metadata 过滤的检索。"""

    def __init__(
        self,
        ids: list[str],
        tokens: list[list[str]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> None:
        if not (len(ids) == len(tokens) == len(metadatas) == len(documents)):
            raise ValueError("BM25 ids/tokens/metadatas/documents 长度不一致")
        self._ids = ids
        self._tokens = tokens
        self._metadatas = metadatas
        self._documents = documents
        self._position_by_id = {chunk_id: index for index, chunk_id in enumerate(ids)}
        self._bm25 = BM25Okapi(tokens) if tokens else None

    @classmethod
    def build(
        cls,
        ids: Sequence[str],
        documents: Sequence[str],
        metadatas: Sequence[dict[str, Any]],
        *,
        payload_documents: Sequence[str] | None = None,
    ) -> BM25Index:
        """从文档正文构建索引（分词一次）。"""
        tokens = [tokenize(doc) for doc in documents]
        stored_documents = list(payload_documents) if payload_documents is not None else list(documents)
        return cls(list(ids), tokens, [dict(m) for m in metadatas], stored_documents)

    def save(self, path: str) -> None:
        """落盘：存 token（非模型），加载时免重分词。"""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": BM25_FORMAT_VERSION,
                    "ids": self._ids,
                    "tokens": self._tokens,
                    "metadatas": self._metadatas,
                    "documents": self._documents,
                },
                f,
                ensure_ascii=False,
            )

    @classmethod
    def load(cls, path: str) -> BM25Index | None:
        """从磁盘加载；文件不存在返回 None，损坏则报错。"""
        p = Path(path)
        if not p.exists():
            return None
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("version") != BM25_FORMAT_VERSION or "documents" not in data:
                raise RuntimeError(
                    "BM25 索引格式过旧，缺少稀疏检索正文。请执行 `uv run python main.py kb build --sparse-only` 重建。"
                )
            return cls(data["ids"], data["tokens"], data["metadatas"], data["documents"])
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise RuntimeError(f"BM25 索引读取失败或已损坏: {path}") from exc

    def get_payload(self, chunk_id: str) -> tuple[str, dict[str, Any]] | None:
        """返回命中分块的原始正文与 metadata，不访问向量数据库。"""
        position = self._position_by_id.get(chunk_id)
        if position is None:
            return None
        return self._documents[position], dict(self._metadatas[position])

    def search(self, query: str, top_n: int, where: dict[str, Any] | None = None) -> list[tuple[str, float]]:
        """检索，返回 [(id, score)]，按分数降序。where 在 Python 侧过滤同域。"""
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        candidates = [
            (self._ids[i], float(scores[i]))
            for i in range(len(self._ids))
            if where is None or _match_where(self._metadatas[i], where)
        ]
        candidates.sort(key=lambda pair: pair[1], reverse=True)
        return candidates[:top_n]


def _match_where(meta: dict[str, Any], where: dict[str, Any]) -> bool:
    """在 Python 侧复刻 ChromaDB where 语义（供 BM25 过滤同域，与 dense 侧对齐）。"""
    for key, cond in where.items():
        if key == "$and":
            if not all(_match_where(meta, sub) for sub in cond):
                return False
        elif key == "$or":
            if not any(_match_where(meta, sub) for sub in cond):
                return False
        elif isinstance(cond, dict):
            if not _match_op(meta.get(key), cond):
                return False
        elif meta.get(key) != cond:  # 隐式 $eq
            return False
    return True


def _match_op(value: Any, cond: dict[str, Any]) -> bool:
    for op, expected in cond.items():
        if op == "$eq" and value != expected:
            return False
        if op == "$ne" and value == expected:
            return False
        if op == "$in" and value not in expected:
            return False
        if op == "$nin" and value in expected:
            return False
        # $contains: list 型字段的成员包含（对齐 ChromaDB 对 list metadata 的 $contains）
        if op == "$contains" and (not isinstance(value, (list, tuple)) or expected not in value):
            return False
    return True
