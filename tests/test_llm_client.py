from __future__ import annotations

from types import SimpleNamespace

from core.llm_client import LLMClient


class _FakeChatCompletions:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))])


class _FakeEmbeddings:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=[1.0, 0.0]), SimpleNamespace(embedding=[0.0, 1.0])]
        )


def test_chat_preserves_zero_temperature() -> None:
    client = LLMClient(base_url="http://example.test", api_key="key", model="model")
    completions = _FakeChatCompletions()
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    result = client.chat("system", "user", temperature=0.0)

    assert completions.kwargs["temperature"] == 0.0
    assert result == '{"ok": true}'


def test_embed_many_sends_single_batch_request() -> None:
    client = LLMClient(base_url="http://example.test", api_key="key", model="model", embed_model="embed-model")
    embeddings = _FakeEmbeddings()
    client._embed_client = SimpleNamespace(embeddings=embeddings)

    result = client.embed_many(["第一段", "第二段"])

    assert embeddings.kwargs["input"] == ["第一段", "第二段"]
    assert result == [[1.0, 0.0], [0.0, 1.0]]


def test_chat_json_requests_json_object_response() -> None:
    client = LLMClient(base_url="http://example.test", api_key="key", model="model")
    completions = _FakeChatCompletions()
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    result = client.chat_json("system", "return json")

    assert completions.kwargs["response_format"] == {"type": "json_object"}
    assert result == {"ok": True}
