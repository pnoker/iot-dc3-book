from __future__ import annotations

import pytest

from core.rag import RAGEngine


def test_rag_rejects_overlap_not_smaller_than_chunk_size(tmp_path) -> None:
    with pytest.raises(ValueError, match="chunk_overlap 必须小于 chunk_size"):
        RAGEngine(embed_fn=lambda text: [0.0], chunk_size=100, chunk_overlap=100, persist_dir=str(tmp_path))


def test_rag_status_reports_empty_index_as_unhealthy(tmp_path) -> None:
    engine = RAGEngine(embed_fn=lambda text: [0.0], persist_dir=str(tmp_path))

    status = engine.get_status()

    assert status["chunk_count"] == 0
    assert status["healthy"] is False
    assert status["persist_dir"] == str(tmp_path)
