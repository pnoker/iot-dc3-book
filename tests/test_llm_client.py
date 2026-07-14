from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.llm_client import LLMClient


class _FakeChatCompletions:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))])


class _FlakyChatCompletions:
    def __init__(self, responses: list[str | Exception]) -> None:
        self.responses = responses
        self.calls = 0
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=response))])


class _FakeEmbeddings:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=[1.0, 0.0]), SimpleNamespace(embedding=[0.0, 1.0])]
        )


class _FlakyEmbeddings:
    def __init__(self, responses: list[list[float] | Exception]) -> None:
        self.responses = responses
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return SimpleNamespace(data=[SimpleNamespace(embedding=response)])


def test_chat_preserves_zero_temperature() -> None:
    client = LLMClient(base_url="http://example.test", api_key="key", model="model")
    completions = _FakeChatCompletions()
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    result = client.chat("system", "user", temperature=0.0)

    assert completions.kwargs["temperature"] == 0.0
    assert result == '{"ok": true}'


def test_embed_many_sends_single_batch_request() -> None:
    client = LLMClient(
        base_url="http://example.test",
        api_key="key",
        model="model",
        embed_base_url="http://embed.example.test",
        embed_api_key="embed-key",
        embed_model="embed-model",
    )
    embeddings = _FakeEmbeddings()
    client._embed_client = SimpleNamespace(embeddings=embeddings)

    result = client.embed_many(["第一段", "第二段"])

    assert embeddings.kwargs["input"] == ["第一段", "第二段"]
    assert result == [[1.0, 0.0], [0.0, 1.0]]


def test_embed_retries_use_embedding_runtime_policy() -> None:
    client = LLMClient(
        base_url="http://example.test",
        api_key="key",
        model="model",
        retry_attempts=1,
        retry_min_seconds=0,
        retry_max_seconds=0,
        embed_base_url="http://embed.example.test",
        embed_api_key="embed-key",
        embed_model="embed-model",
        embed_retry_attempts=2,
        embed_retry_min_seconds=0,
        embed_retry_max_seconds=0,
    )
    embeddings = _FlakyEmbeddings([ConnectionError("embed down"), [1.0, 0.0]])
    client._embed_client = SimpleNamespace(embeddings=embeddings)

    result = client.embed("第一段")

    assert embeddings.calls == 2
    assert result == [1.0, 0.0]


def test_chat_json_requests_json_object_response() -> None:
    client = LLMClient(base_url="http://example.test", api_key="key", model="model")
    completions = _FakeChatCompletions()
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    result = client.chat_json("system", "return json")

    assert completions.kwargs["response_format"] == {"type": "json_object"}
    assert result == {"ok": True}


def test_chat_retries_retryable_network_errors() -> None:
    client = LLMClient(
        base_url="http://example.test",
        api_key="key",
        model="model",
        retry_attempts=2,
        retry_min_seconds=0,
        retry_max_seconds=0,
    )
    completions = _FlakyChatCompletions([ConnectionError("network down"), '{"ok": true}'])
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    result = client.chat("system", "user")

    assert completions.calls == 2
    assert result == '{"ok": true}'


def test_chat_does_not_retry_non_retryable_errors() -> None:
    client = LLMClient(
        base_url="http://example.test",
        api_key="key",
        model="model",
        retry_attempts=3,
        retry_min_seconds=0,
        retry_max_seconds=0,
    )
    completions = _FlakyChatCompletions([ValueError("bad request")])
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    with pytest.raises(ValueError, match="bad request"):
        client.chat("system", "user")

    assert completions.calls == 1


def test_chat_json_retries_parse_failures() -> None:
    client = LLMClient(
        base_url="http://example.test",
        api_key="key",
        model="model",
        retry_min_seconds=0,
        retry_max_seconds=0,
        json_retry_attempts=2,
    )
    completions = _FlakyChatCompletions(["不是 JSON", '{"ok": true}'])
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    result = client.chat_json("system", "return json")

    assert completions.calls == 2
    assert result == {"ok": True}


def test_chat_json_allows_per_call_json_retry_override() -> None:
    client = LLMClient(
        base_url="http://example.test",
        api_key="key",
        model="model",
        retry_min_seconds=0,
        retry_max_seconds=0,
        json_retry_attempts=2,
    )
    completions = _FlakyChatCompletions(["不是 JSON", '{"ok": true}'])
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    with pytest.raises(ValueError, match="无法从 LLM 响应中解析 JSON"):
        client.chat_json("system", "return json", json_retry_attempts=1)

    assert completions.calls == 1
