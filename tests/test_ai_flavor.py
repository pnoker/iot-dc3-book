from __future__ import annotations

from core.ai_flavor import detect_ai_flavor


def test_detects_cliche_phrases() -> None:
    text = "在当今数字化时代，物联网蓬勃发展。综上所述，这为智能制造奠定了坚实基础。"
    issues = detect_ai_flavor(text)
    assert len(issues) == 1
    assert "AI 套话" in issues[0]
    assert "3 处" in issues[0]  # 在当今…时代 / 综上所述 / 奠定了…基础


def test_detects_bold_overuse() -> None:
    text = ("物联网技术" * 200) + "".join(f"**要点{i}**是关键。" for i in range(30))
    issues = detect_ai_flavor(text)
    assert any("加粗过密" in i for i in issues)


def test_clean_text_no_issue() -> None:
    text = (
        "Modbus 采用主从架构，主站轮询从站寄存器。这种设计在工业现场简单可靠，"
        "但轮询延迟会随从站数量线性增长，规模大时要改用事件上报或分组轮询。"
    )
    assert detect_ai_flavor(text) == []


def test_bold_overuse_ignored_for_short_text() -> None:
    # 不足 500 字的短文本不做加粗密度判定，避免误报
    text = "**核心**在于**解耦**与**可观测**。"
    assert not any("加粗过密" in i for i in detect_ai_flavor(text))


def test_cliche_hits_deduplicated_in_message() -> None:
    text = "值得注意的是，A 很重要。值得注意的是，B 也重要。值得注意的是，C 同样重要。"
    issues = detect_ai_flavor(text)
    assert "3 处" in issues[0]  # 计数是 3
    assert issues[0].count("值得注意的是") == 1  # 示例里去重只显示一次
