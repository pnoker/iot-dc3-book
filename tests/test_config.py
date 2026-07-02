"""core.config 单元测试"""

from core.config import _resolve_env_var, config_to_book_state, load_config


def test_resolve_env_var_literal():
    assert _resolve_env_var("sk-abc123") == "sk-abc123"


def test_resolve_env_var_missing(monkeypatch):
    monkeypatch.delenv("TEST_VAR_XYZ", raising=False)
    result = _resolve_env_var("${TEST_VAR_XYZ}")
    assert result == ""


def test_resolve_env_var_set(monkeypatch):
    monkeypatch.setenv("TEST_VAR_XYZ", "secret")
    assert _resolve_env_var("${TEST_VAR_XYZ}") == "secret"


def test_config_to_book_state():
    cfg = {
        "book": {"title": "Test", "subtitle": "Sub"},
        "parts": [{"name": "Part1", "prefix": "一", "chapters": [{"id": 1, "title": "Ch1", "summary": "Summary"}]}],
        "style": {"tone": "professional", "forbidden_words": ["bad"]},
    }
    state = config_to_book_state(cfg)
    assert state.book_title == "Test"
    assert len(state.parts) == 1
    assert state.parts[0].chapters[0].title == "Ch1"
    assert state.style.forbidden_words == ["bad"]


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
