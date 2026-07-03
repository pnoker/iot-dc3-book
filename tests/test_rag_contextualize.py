from __future__ import annotations

from core.rag_contextualize import contextualize_chunk


class FakeLLM:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls = 0

    def chat(self, system: str, user: str, temperature=None, max_tokens=None) -> str:
        self.calls += 1
        return self.reply


def test_contextualize_prepends_context() -> None:
    llm = FakeLLM("讲解 Modbus 协议的帧结构")
    out = contextualize_chunk(llm, "drivers/modbus.md", "协议解析", "Modbus 帧由地址域和功能码组成。")

    assert out.startswith("[情境] 讲解 Modbus 协议的帧结构")
    assert "Modbus 帧由地址域和功能码组成。" in out  # 原文保留


def test_contextualize_returns_original_on_empty_reply() -> None:
    llm = FakeLLM("   ")
    original = "一段正文内容。"
    out = contextualize_chunk(llm, "s", "sec", original)

    assert out == original  # 空回复回退原文


def test_contextualize_returns_original_on_llm_error() -> None:
    class BoomLLM:
        def chat(self, *a, **k):
            raise RuntimeError("boom")

    original = "一段正文内容。"
    out = contextualize_chunk(BoomLLM(), "s", "sec", original)

    assert out == original  # LLM 异常不外抛，回退原文
