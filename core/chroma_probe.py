"""在独立进程中探测 Chroma 原生存储，隔离不可捕获的 native crash。"""

from __future__ import annotations

import sys

import chromadb
from chromadb.config import Settings


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m core.chroma_probe <persist-dir>", file=sys.stderr)
        return 2
    try:
        client = chromadb.PersistentClient(
            path=sys.argv[1],
            settings=Settings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection(
            name="books",
            metadata={"hnsw:space": "cosine"},
        )
        print(collection.count())
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
