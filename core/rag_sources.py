"""
RAG 参考来源遍历 - 供索引器与 manifest 共用的唯一文件发现逻辑

索引 (rag.index_books) 与签名 (rag_manifest.build_manifest) 必须遍历完全相同的
文件集，否则会出现「改了配置不触发重建」或「每次误重建」。二者统一调用
iter_source_files，从结构上消除这类不一致。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.log import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

logger = get_logger("rag")

SUPPORTED_EXTENSIONS = frozenset({".pdf", ".md", ".markdown"})
IGNORE_DIRS = frozenset({"node_modules", ".vitepress", ".git", "__pycache__"})

# 扩展名 → doc_type 归类
_DOC_TYPE_BY_SUFFIX = {".pdf": "book", ".md": "docs", ".markdown": "docs"}


@dataclass(frozen=True)
class ReferenceSource:
    """一个参考来源目录及其分类配置。

    - label 用于命名空间和溯源。
    - categories 为基础分类标签；dir_categories 按子目录首段追加标签。
    - language 标注来源语言。
    """

    path: Path
    label: str
    categories: tuple[str, ...] = ()
    dir_categories: tuple[tuple[str, tuple[str, ...]], ...] = ()  # ((子目录名, (标签...)),) —— 用元组以支持 frozen
    language: str = "zh"


@dataclass(frozen=True)
class SourceFile:
    """来源目录下的一个待索引文件，携带已解析的分类元数据。"""

    label: str
    rel: str  # 相对来源根的 POSIX 路径，跨来源不保证唯一，配合 label 才唯一
    abs_path: Path
    suffix: str  # 小写扩展名，如 ".pdf"
    categories: tuple[str, ...]  # 最终分类（base ∪ 子目录标签），已去重排序
    doc_type: str  # book / docs
    language: str


def _resolve_categories(source: ReferenceSource, rel: str) -> tuple[str, ...]:
    """base 分类 ∪ 子目录首段命中的标签；均为空时回退到 label，避免孤儿 chunk。"""
    tags = set(source.categories)
    first_segment = rel.split("/", 1)[0]
    for dir_name, dir_tags in source.dir_categories:
        if dir_name == first_segment:
            tags.update(dir_tags)
    if not tags:
        tags.add(source.label)
    return tuple(sorted(tags))


def iter_source_files(sources: Sequence[ReferenceSource]) -> list[SourceFile]:
    """遍历所有来源，返回受支持格式的文件，按 (label, rel) 排序保证确定性。"""
    files: list[SourceFile] = []
    for source in sources:
        root = source.path
        if not root.exists():
            logger.warning("参考来源目录不存在，跳过: %s", root)
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in IGNORE_DIRS for part in path.relative_to(root).parts):
                continue
            suffix = path.suffix.lower()
            if suffix not in SUPPORTED_EXTENSIONS:
                continue
            rel = path.relative_to(root).as_posix()
            files.append(
                SourceFile(
                    label=source.label,
                    rel=rel,
                    abs_path=path,
                    suffix=suffix,
                    categories=_resolve_categories(source, rel),
                    doc_type=_DOC_TYPE_BY_SUFFIX.get(suffix, "other"),
                    language=source.language,
                )
            )
    files.sort(key=lambda f: (f.label, f.rel))
    return files
