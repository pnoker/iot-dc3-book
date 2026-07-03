from __future__ import annotations

from pathlib import Path

from core.rag_manifest import build_manifest
from core.rag_markdown import extract_markdown_sections
from core.rag_sources import ReferenceSource, iter_source_files


def _write(path: Path, text: str) -> str:
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_extract_strips_frontmatter_and_uses_title_for_intro(tmp_path) -> None:
    md = _write(
        tmp_path / "a.md",
        "---\ntitle: DC3 架构\n---\n开篇正文，介绍平台。\n\n## 第一节\n第一节内容。",
    )

    sections = extract_markdown_sections(md)

    assert sections[0]["section"] == "DC3 架构"  # 首块用 frontmatter title
    assert "开篇正文" in sections[0]["text"]
    assert "title:" not in sections[0]["text"]  # frontmatter 不进正文
    assert sections[1]["section"] == "第一节"


def test_extract_removes_container_markers_but_keeps_inner_prose(tmp_path) -> None:
    md = _write(
        tmp_path / "b.md",
        "# 标题\n::: warning 注意\n工具调用默认开启。\n:::\n后续说明。",
    )

    text = extract_markdown_sections(md)[0]["text"]

    assert ":::" not in text  # 容器标记被删
    assert "工具调用默认开启" in text  # 内部正文保留
    assert "后续说明" in text


def test_extract_preserves_colons_inside_code_fence(tmp_path) -> None:
    md = _write(
        tmp_path / "c.md",
        "# 配置\n```yaml\nkey: value\n:::not-a-container\n```\n正文。",
    )

    text = extract_markdown_sections(md)[0]["text"]

    assert ":::not-a-container" in text  # 围栏内的 ::: 不被误删


def test_extract_drops_script_block(tmp_path) -> None:
    md = _write(
        tmp_path / "d.md",
        "# 页\n<script setup>\nimport x from 'y'\n</script>\n真实正文。",
    )

    text = extract_markdown_sections(md)[0]["text"]

    assert "import x" not in text  # script 块被删
    assert "真实正文" in text


def test_extract_keeps_inline_tags_as_technical_text(tmp_path) -> None:
    md = _write(
        tmp_path / "e.md",
        "# 接口\n路径为 <host>:<port>/api，返回 List<String>。",
    )

    text = extract_markdown_sections(md)[0]["text"]

    assert "<host>:<port>" in text  # 行内标签是技术正文，保留
    assert "List<String>" in text


def test_manifest_is_deterministic_and_namespaced(tmp_path) -> None:
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    _write(root_a / "index.md", "# A\nA 内容。")
    _write(root_b / "index.md", "# B\nB 内容。")
    sources = [ReferenceSource(root_a, "sa"), ReferenceSource(root_b, "sb")]

    m1 = build_manifest(sources, 1000, 200)
    m2 = build_manifest(sources, 1000, 200)

    assert m1 == m2  # 确定性
    entries = m1["files"]
    labels = {(e["source"], e["path"]) for e in entries}
    assert ("sa", "index.md") in labels  # 同名 index.md 按 label 命名空间区分
    assert ("sb", "index.md") in labels


def test_manifest_changes_when_sources_or_chunking_change(tmp_path) -> None:
    root = tmp_path / "a"
    root.mkdir()
    _write(root / "x.md", "# X\nX 内容。")
    base = [ReferenceSource(root, "sa")]

    m_base = build_manifest(base, 1000, 200)
    m_chunk = build_manifest(base, 800, 200)
    root2 = tmp_path / "b"
    root2.mkdir()
    _write(root2 / "y.md", "# Y\nY 内容。")
    m_more = build_manifest([*base, ReferenceSource(root2, "sb")], 1000, 200)

    assert m_base != m_chunk  # chunk_size 变 → 触发重建
    assert m_base != m_more  # 增来源 → 触发重建


def test_manifest_changes_when_embed_model_or_contextualize_change(tmp_path) -> None:
    root = tmp_path / "a"
    root.mkdir()
    _write(root / "x.md", "# X\nX 内容。")
    base = [ReferenceSource(root, "sa")]

    m_base = build_manifest(base, 1000, 200, embed_model="model-a", contextualize=False)
    m_model = build_manifest(base, 1000, 200, embed_model="model-b", contextualize=False)
    m_ctx = build_manifest(base, 1000, 200, embed_model="model-a", contextualize=True)

    assert m_base != m_model  # 换嵌入模型 → 触发重建（否则新旧向量空间错位）
    assert m_base != m_ctx  # 开关情境化 → 触发重建（否则开关形同虚设）


def test_iter_source_files_ignores_noise_dirs(tmp_path) -> None:
    root = tmp_path / "docs"
    (root / "node_modules").mkdir(parents=True)
    (root / "ok").mkdir()
    _write(root / "node_modules" / "junk.md", "垃圾")
    _write(root / "ok" / "real.md", "真实")

    files = iter_source_files([ReferenceSource(root, "d")])

    rels = {f.rel for f in files}
    assert "ok/real.md" in rels
    assert not any("node_modules" in r for r in rels)  # 噪音目录被忽略


def test_source_file_resolves_base_and_dir_categories(tmp_path) -> None:
    root = tmp_path / "docs"
    (root / "ai").mkdir(parents=True)
    (root / "misc").mkdir()
    _write(root / "ai" / "a.md", "# A\nAI 内容。")
    _write(root / "misc" / "b.md", "# B\n杂项。")
    src = ReferenceSource(
        root,
        "dc3",
        categories=("iot", "dc3"),
        dir_categories=(("ai", ("ai", "agentic")),),
        language="zh",
    )

    files = {f.rel: f for f in iter_source_files([src])}

    # ai 子目录追加标签，且 base ∪ dir 去重排序
    assert files["ai/a.md"].categories == ("agentic", "ai", "dc3", "iot")
    assert files["ai/a.md"].doc_type == "docs"
    assert files["ai/a.md"].language == "zh"
    # 未命中子目录规则只保留 base
    assert files["misc/b.md"].categories == ("dc3", "iot")


def test_source_file_falls_back_to_label_when_no_categories(tmp_path) -> None:
    root = tmp_path / "books"
    root.mkdir()
    _write(root / "x.md", "# X\n内容。")

    files = iter_source_files([ReferenceSource(root, "mybooks")])

    assert files[0].categories == ("mybooks",)  # 无分类配置时回退 label，避免孤儿
