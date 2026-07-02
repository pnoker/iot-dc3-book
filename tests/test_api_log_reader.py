from __future__ import annotations

from typing import TYPE_CHECKING

from api.log_reader import mask_secrets, parse_log_line, read_logs

if TYPE_CHECKING:
    from pathlib import Path


def test_mask_secrets_hides_api_keys() -> None:
    text = "DEEPSEEK_API_KEY=sk-1234567890abcdef OPENROUTER_API_KEY=or-abcdef1234567890"

    masked = mask_secrets(text)

    assert "1234567890abcdef" not in masked
    assert "abcdef1234567890" not in masked
    assert "DEEPSEEK_API_KEY=sk-****" in masked
    assert "OPENROUTER_API_KEY=or-****" in masked


def test_parse_log_line_extracts_structured_fields() -> None:
    line = "2026-07-02 17:05:25 | INFO    | book_writer.WriterAgent | 撰写第2章 物联网体系架构..."

    entry = parse_log_line(line)

    assert entry.timestamp == "2026-07-02 17:05:25"
    assert entry.level == "INFO"
    assert entry.logger == "book_writer.WriterAgent"
    assert entry.agent == "WriterAgent"
    assert entry.chapter_id == 2
    assert entry.message == "撰写第2章 物联网体系架构..."


def test_read_logs_filters_and_limits_entries(tmp_path: Path) -> None:
    log_file = tmp_path / "book-writer.log"
    log_file.write_text(
        "\n".join(
            [
                "2026-07-02 17:05:00 | INFO    | book_writer.ResearchAgent | 检索第2章 物联网体系架构 的参考资料...",
                "2026-07-02 17:05:25 | INFO    | book_writer.WriterAgent | 撰写第2章 物联网体系架构...",
                "2026-07-02 17:07:09 | ERROR   | book_writer.FactCheckerAgent | 第2章事实核查失败 OPENROUTER_API_KEY=or-secretsecret",
                "2026-07-02 17:10:46 | INFO    | book_writer.ResearchAgent | 检索第3章 感知层技术基础 的参考资料...",
            ]
        ),
        encoding="utf-8",
    )

    entries = read_logs(log_file, level="ERROR", chapter=2, limit=10)

    assert len(entries) == 1
    assert entries[0].level == "ERROR"
    assert entries[0].agent == "FactCheckerAgent"
    assert entries[0].chapter_id == 2
    assert "secretsecret" not in entries[0].message

    recent = read_logs(log_file, limit=2)
    assert [entry.chapter_id for entry in recent] == [2, 3]
