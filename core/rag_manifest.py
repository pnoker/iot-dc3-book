"""
RAG 索引输入签名工具
"""

from __future__ import annotations

import json
from pathlib import Path


def build_manifest(books_dir: str, chunk_size: int, chunk_overlap: int) -> dict[str, object]:
    """构建参考书索引输入签名，用于判断索引是否过期。"""
    books_path = Path(books_dir)
    files: list[dict[str, object]] = []
    if books_path.exists():
        for pdf_file in sorted(books_path.rglob("*.pdf")):
            stat = pdf_file.stat()
            files.append(
                {
                    "path": str(pdf_file.relative_to(books_path)),
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                }
            )
    return {
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "files": files,
    }


def manifest_matches(index_path: str, manifest: dict[str, object]) -> bool:
    """判断现有索引签名是否与当前输入一致。"""
    if not index_path:
        return False
    path = Path(index_path)
    if not path.exists():
        return False
    try:
        with open(path, encoding="utf-8") as f:
            return bool(json.load(f) == manifest)
    except (OSError, json.JSONDecodeError):
        return False


def write_manifest(index_path: str, manifest: dict[str, object]) -> None:
    """写入索引签名。"""
    if not index_path:
        return
    path = Path(index_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
