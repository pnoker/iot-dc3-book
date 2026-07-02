"""core.config 单元测试"""

from pathlib import Path

from core.config import (
    AppConfig,
    config_to_app_config,
    config_to_book_state,
    get_embed_config,
    get_llm_config,
    load_config,
    load_env_settings,
)


def test_load_env_settings_reads_dotenv(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        'DEEPSEEK_API_KEY="deepseek-from-dotenv"\nOPENROUTER_API_KEY=openrouter-from-dotenv\n',
        encoding="utf-8",
    )

    settings = load_env_settings(env_file)

    assert settings.deepseek_api_key == "deepseek-from-dotenv"
    assert settings.openrouter_api_key == "openrouter-from-dotenv"


def test_env_example_documents_required_keys():
    with open(".env.example", encoding="utf-8") as f:
        content = f.read()

    assert "DEEPSEEK_API_KEY=" in content
    assert "OPENROUTER_API_KEY=" in content


def test_config_to_book_state():
    cfg = {
        "book": {"title": "Test", "subtitle": "Sub"},
        "parts": [{"name": "Part1", "prefix": "一", "chapters": [{"id": 1, "title": "Ch1", "summary": "Summary"}]}],
        "style": {"tone": "professional", "forbidden_words": ["bad"]},
        "llm": {"base_url": "https://example.test", "model": "model"},
    }
    state = config_to_book_state(cfg)
    assert state.book_title == "Test"
    assert len(state.parts) == 1
    assert state.parts[0].chapters[0].title == "Ch1"
    assert state.style.forbidden_words == ["bad"]


def test_config_to_app_config_returns_typed_models():
    cfg = load_config("config")

    app_config = config_to_app_config(cfg)

    assert isinstance(app_config, AppConfig)
    assert app_config.book.title == "物联网技术与实践"
    assert app_config.llm.embedding.model == "qwen/qwen3-embedding-8b"
    assert app_config.references.chunk_size > app_config.references.chunk_overlap


def test_get_llm_config_uses_pydantic_settings(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("DEEPSEEK_API_KEY=deepseek-from-env\n", encoding="utf-8")
    cfg = {
        "book": {"title": "Test", "subtitle": "Sub"},
        "parts": [{"name": "Part1", "prefix": "一", "chapters": [{"id": 1, "title": "Ch1"}]}],
        "style": {},
        "llm": {"base_url": "https://example.test", "model": "model"},
    }

    llm_cfg = get_llm_config(cfg)

    assert llm_cfg["api_key"] == "deepseek-from-env"


def test_get_embed_config_uses_pydantic_settings(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("OPENROUTER_API_KEY=openrouter-from-env\n", encoding="utf-8")
    cfg = {
        "book": {"title": "Test", "subtitle": "Sub"},
        "parts": [{"name": "Part1", "prefix": "一", "chapters": [{"id": 1, "title": "Ch1"}]}],
        "style": {},
        "llm": {"embedding": {"base_url": "https://embed.test", "model": "embed-model"}},
    }

    embed_cfg = get_embed_config(cfg)

    assert embed_cfg["embed_api_key"] == "openrouter-from-env"


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
