"""
RAG 索引输入签名工具
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from core.rag_sources import SUPPORTED_EXTENSIONS, iter_source_files

if TYPE_CHECKING:
    from collections.abc import Sequence

    from core.rag_sources import ReferenceSource


def build_manifest(
        sources: Sequence[ReferenceSource],
        chunk_size: int,
        chunk_overlap: int,
        embed_model: str = "",
        contextualize: bool = False,
) -> dict[str, object]:
    """构建参考来源索引输入签名，用于判断索引是否过期。

    条目按 label 命名空间，避免不同来源下同名文件（如多个 index.md）相互别名；
    签名含 sources 与 extensions，配置层变化（增删来源、支持新格式）也会触发重建。
    embed_model 与 contextualize 同样改变入库向量/正文，纳入签名以免换模型或
    开关情境化后仍误判「未变化，跳过构建」而检索劣化。
    """
    files: list[dict[str, object]] = []
    for source_file in iter_source_files(sources):
        stat = source_file.abs_path.stat()
        files.append(
            {
                "source": source_file.label,
                "path": source_file.rel,
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
        )
    return {
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "embed_model": embed_model,
        "contextualize": contextualize,
        "sources": [_source_signature(s) for s in sources],
        "extensions": sorted(SUPPORTED_EXTENSIONS),
        "files": files,
    }


def _source_signature(source: ReferenceSource) -> dict[str, object]:
    """来源签名：路径与分类配置变化都应触发重建（会改变 chunk metadata）。"""
    return {
        "label": source.label,
        "path": str(source.path),
        "categories": list(source.categories),
        "dir_categories": [[name, list(tags)] for name, tags in source.dir_categories],
        "language": source.language,
    }


def manifest_matches(index_path: str, manifest: dict[str, object]) -> bool:
    """判断现有索引签名是否与当前输入一致。"""
    existing = read_manifest(index_path)
    return bool(existing == manifest)


def read_manifest(index_path: str) -> dict[str, object] | None:
    """读取索引签名；不存在返回 None，损坏则报错。"""
    if not index_path:
        return None
    path = Path(index_path)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"RAG manifest 读取失败或已损坏: {path}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"RAG manifest 格式错误，顶层必须是对象: {path}")
    return data


def manifest_static_matches(old: dict[str, object] | None, new: dict[str, object]) -> bool:
    """判断除文件列表外的索引配置是否一致。"""
    if old is None:
        return False
    for key in ("chunk_size", "chunk_overlap", "embed_model", "contextualize", "sources", "extensions"):
        if old.get(key) != new.get(key):
            return False
    return True


def manifest_file_map(manifest: dict[str, object] | None) -> dict[tuple[str, str], dict[str, object]]:
    """把 manifest.files 转成 {(source, path): file_signature} 映射。"""
    if manifest is None:
        return {}
    files = manifest.get("files")
    if not isinstance(files, list):
        return {}
    result: dict[tuple[str, str], dict[str, object]] = {}
    for item in files:
        if not isinstance(item, dict):
            continue
        source = item.get("source")
        path = item.get("path")
        if isinstance(source, str) and isinstance(path, str):
            result[(source, path)] = item
    return result


def write_manifest(index_path: str, manifest: dict[str, object]) -> None:
    """写入索引签名。"""
    if not index_path:
        return
    path = Path(index_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
