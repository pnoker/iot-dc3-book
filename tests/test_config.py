"""core.config 单元测试"""

import re
from pathlib import Path

import pytest

from core.config import (
    AppConfig,
    config_to_app_config,
    config_to_book_state,
    get_config_paths,
    get_embed_config,
    get_llm_config,
    load_app_config,
    load_config,
    load_env_settings,
)


def _minimal_config(*, llm: dict[str, object] | None = None, references: dict[str, object] | None = None) -> dict[str, object]:
    references_config = {"sources": [{"path": "../books", "label": "books", "categories": ["iot"]}]} if references is None else references
    return {
        "book": {"title": "Test", "subtitle": "Sub"},
        "parts": [{"name": "Part1", "prefix": "一", "chapters": [{"id": 1, "title": "Ch1", "summary": "Summary"}]}],
        "style": {"tone": "professional", "forbidden_words": ["bad"]},
        "llm": llm
        or {
            "base_url": "https://example.test",
            "api_key": "test-chat-key",
            "model": "model",
            "embedding": {
                "base_url": "https://embed.test",
                "api_key": "test-embed-key",
                "model": "embed-model",
            },
        },
        "references": references_config,
    }


def test_load_env_settings_reads_dotenv(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-from-shell")
    env_file = tmp_path / ".env"
    env_file.write_text(
        'DEEPSEEK_API_KEY="deepseek-from-dotenv"\nOPENROUTER_API_KEY=openrouter-from-dotenv\n',
        encoding="utf-8",
    )

    settings = load_env_settings(env_file)

    assert settings["DEEPSEEK_API_KEY"] == "deepseek-from-dotenv"
    assert settings["OPENROUTER_API_KEY"] == "openrouter-from-shell"


def test_env_example_documents_required_keys():
    with open(".env.example", encoding="utf-8") as f:
        content = f.read()

    assert "DEEPSEEK_API_KEY=" in content
    assert "OPENROUTER_API_KEY=" in content


def test_config_to_book_state():
    cfg = _minimal_config()
    state = config_to_book_state(cfg)
    assert state.book_title == "Test"
    assert len(state.parts) == 1
    assert state.parts[0].chapters[0].title == "Ch1"
    assert state.style.forbidden_words == ["bad"]
    assert state.max_revision_count == 5
    assert state.max_final_revision_round == 1
    assert state.quality.continue_on_failure is True
    assert state.writing.parallel_chapters is True
    assert state.writing.parallel_workers == 3


def test_config_to_app_config_returns_typed_models(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    cfg = load_config("config")

    app_config = config_to_app_config(cfg)

    assert isinstance(app_config, AppConfig)
    assert app_config.book.title == "物联网技术与实践"
    assert app_config.llm.embedding.model == "qwen/qwen3-embedding-8b"
    assert app_config.references.chunk_size > app_config.references.chunk_overlap
    assert app_config.references.web_research.enabled is False
    assert app_config.writing.parallel_chapters is True
    assert app_config.writing.parallel_workers == 3
    assert app_config.quality.require_exercises is False
    assert app_config.quality.max_revision_rounds == 5
    assert app_config.quality.min_figures_per_section == 1
    assert app_config.quality.continue_on_failure is True
    assert app_config.style.illustrations.marker == "book-figure"
    assert "architecture" in app_config.style.illustrations.allowed_types


def test_load_app_config_resolves_paths_from_project_root(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    config_dir = tmp_path / "project" / "config"
    config_dir.mkdir(parents=True)
    (tmp_path / "project" / ".env").write_text(
        "DEEPSEEK_API_KEY=deepseek-from-project\nOPENROUTER_API_KEY=openrouter-from-project\n",
        encoding="utf-8",
    )
    (config_dir / "book.yaml").write_text('title: "Test"\nsubtitle: "Sub"\n', encoding="utf-8")
    (config_dir / "parts.yaml").write_text(
        '- name: "Part1"\n  prefix: "一"\n  chapters:\n    - id: 1\n      title: "Ch1"\n',
        encoding="utf-8",
    )
    (config_dir / "style.yaml").write_text("{}\n", encoding="utf-8")
    (config_dir / "llm.yaml").write_text(
        'base_url: "https://chat.test"\napi_key: "${DEEPSEEK_API_KEY}"\nmodel: "chat-model"\nembedding:\n  base_url: "https://embed.test"\n  api_key: "${OPENROUTER_API_KEY}"\n  model: "embed-model"\n',
        encoding="utf-8",
    )
    (config_dir / "references.yaml").write_text(
        'sources:\n  - path: "../books"\n    label: "books"\n    categories: ["iot"]\n',
        encoding="utf-8",
    )
    (config_dir / "output.yaml").write_text('dir: "./output"\n', encoding="utf-8")

    app_config = load_app_config(str(config_dir))
    paths = get_config_paths(app_config)

    assert app_config.llm.api_key.get_secret_value() == "deepseek-from-project"
    assert app_config.llm.embedding.api_key.get_secret_value() == "openrouter-from-project"
    assert paths.project_dir == tmp_path / "project"
    assert paths.reference_sources[0].path == tmp_path / "books"
    assert paths.output_dir == tmp_path / "project" / "output"
    assert paths.data_dir == tmp_path / "project" / ".data"


def test_load_app_config_rejects_unknown_keys(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "book.yaml").write_text('title: "Test"\nsubtitle: "Sub"\nunknown: true\n', encoding="utf-8")
    (config_dir / "parts.yaml").write_text(
        '- name: "Part1"\n  prefix: "一"\n  chapters:\n    - id: 1\n      title: "Ch1"\n',
        encoding="utf-8",
    )
    (config_dir / "style.yaml").write_text("{}\n", encoding="utf-8")
    (config_dir / "llm.yaml").write_text(
        'base_url: "https://chat.test"\napi_key: "chat-key"\nmodel: "chat-model"\nembedding:\n  base_url: "https://embed.test"\n  api_key: "embed-key"\n  model: "embed-model"\n',
        encoding="utf-8",
    )
    (config_dir / "references.yaml").write_text(
        'sources:\n  - path: "../books"\n    label: "books"\n    categories: ["iot"]\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown"):
        load_app_config(str(config_dir))


def test_get_llm_config_resolves_yaml_env_placeholder(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("DEEPSEEK_API_KEY=deepseek-from-env\n", encoding="utf-8")
    cfg = _minimal_config(
        llm={
            "base_url": "https://example.test",
            "api_key": "${DEEPSEEK_API_KEY}",
            "model": "model",
            "embedding": {
                "base_url": "https://embed.test",
                "api_key": "test-embed-key",
                "model": "embed-model",
            },
        }
    )

    llm_cfg = get_llm_config(cfg)

    assert llm_cfg["api_key"] == "deepseek-from-env"


def test_get_llm_config_includes_runtime_policy() -> None:
    cfg = _minimal_config(
        llm={
            "base_url": "https://example.test",
            "api_key": "test-chat-key",
            "model": "model",
            "temperature": 0.2,
            "max_tokens": 4096,
            "timeout_seconds": 60,
            "retry_attempts": 5,
            "retry_min_seconds": 1,
            "retry_max_seconds": 20,
            "json_retry_attempts": 3,
            "embedding": {
                "base_url": "https://embed.test",
                "api_key": "test-embed-key",
                "model": "embed-model",
            },
        }
    )

    llm_cfg = get_llm_config(cfg)

    assert llm_cfg["timeout"] == 60
    assert llm_cfg["retry_attempts"] == 5
    assert llm_cfg["retry_min_seconds"] == 1
    assert llm_cfg["retry_max_seconds"] == 20
    assert llm_cfg["json_retry_attempts"] == 3


def test_llm_runtime_policy_validates_retry_bounds() -> None:
    cfg = _minimal_config(
        llm={
            "base_url": "https://example.test",
            "api_key": "test-chat-key",
            "model": "model",
            "retry_min_seconds": 10,
            "retry_max_seconds": 1,
            "embedding": {
                "base_url": "https://embed.test",
                "api_key": "test-embed-key",
                "model": "embed-model",
            },
        }
    )

    with pytest.raises(ValueError, match="retry_max_seconds"):
        config_to_app_config(cfg)


def test_get_embed_config_resolves_yaml_env_placeholder(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("OPENROUTER_API_KEY=openrouter-from-env\n", encoding="utf-8")
    cfg = _minimal_config(
        llm={
            "base_url": "https://example.test",
            "api_key": "test-chat-key",
            "model": "model",
            "embedding": {
                "base_url": "https://embed.test",
                "api_key": "${OPENROUTER_API_KEY}",
                "model": "embed-model",
            }
        },
    )

    embed_cfg = get_embed_config(cfg)

    assert embed_cfg["embed_api_key"] == "openrouter-from-env"


def test_env_values_are_not_injected_without_yaml_placeholder(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("DEEPSEEK_API_KEY=deepseek-from-env\n", encoding="utf-8")
    cfg = _minimal_config()

    llm_cfg = get_llm_config(cfg)

    assert llm_cfg["api_key"] == "test-chat-key"


def test_missing_yaml_env_placeholder_fails_fast(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    cfg = _minimal_config(
        llm={
            "base_url": "https://example.test",
            "api_key": "${DEEPSEEK_API_KEY}",
            "model": "model",
            "embedding": {
                "base_url": "https://embed.test",
                "api_key": "test-embed-key",
                "model": "embed-model",
            },
        }
    )

    with pytest.raises(ValueError, match=re.escape("配置 配置.llm.api_key 引用了未设置的环境变量: DEEPSEEK_API_KEY")):
        config_to_app_config(cfg)


def test_app_config_masks_api_keys_in_python_dump() -> None:
    app_config = config_to_app_config(_minimal_config())

    dumped = app_config.model_dump()

    assert str(dumped["llm"]["api_key"]) == "**********"
    assert str(dumped["llm"]["embedding"]["api_key"]) == "**********"


def test_references_sources_are_required() -> None:
    cfg = _minimal_config(references={})

    with pytest.raises(ValueError, match=re.escape("references.sources")):
        config_to_app_config(cfg)


def test_load_config_dir():
    cfg = load_config("config")
    assert "book" in cfg
    assert "parts" in cfg
    assert "style" in cfg
    assert "llm" in cfg
    assert cfg["book"]["title"] == "物联网技术与实践"


def test_load_config_dir_has_author():
    cfg = load_config("config")
    assert "author" in cfg
    assert "profile" in cfg["author"]
    assert "preface" in cfg["author"]
