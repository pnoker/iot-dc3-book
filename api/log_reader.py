"""Dashboard 日志读取与脱敏工具。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

LOG_PATTERN = re.compile(r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| (?P<level>\w+)\s+\| (?P<logger>[\w.]+)\s+\| (?P<message>.*)$")
CHAPTER_PATTERN = re.compile(r"第(?P<chapter>\d+)章")
SECRET_PATTERNS = (
    re.compile(
        r"(?P<name>[A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*)=(?P<prefix>[A-Za-z0-9]{2}-?)[A-Za-z0-9_./+=-]+"
    ),
)


@dataclass(frozen=True)
class LogEntry:
    timestamp: str
    level: str
    logger: str
    agent: str
    message: str
    raw: str
    chapter_id: int | None = None


def mask_secrets(text: str) -> str:
    """隐藏日志中可能出现的密钥。"""
    masked = text
    for pattern in SECRET_PATTERNS:
        masked = pattern.sub(lambda match: f"{match.group('name')}={match.group('prefix')}****", masked)
    return masked


def parse_log_line(line: str) -> LogEntry:
    """解析单行 book_writer 日志。"""
    safe_line = mask_secrets(line.rstrip("\n"))
    match = LOG_PATTERN.match(safe_line)
    if not match:
        return LogEntry(timestamp="", level="", logger="", agent="", message=safe_line, raw=safe_line)
    logger_name = match.group("logger").strip()
    agent = logger_name.removeprefix("book_writer.")
    message = match.group("message")
    chapter_match = CHAPTER_PATTERN.search(message)
    chapter_id = int(chapter_match.group("chapter")) if chapter_match else None
    return LogEntry(
        timestamp=match.group("timestamp"),
        level=match.group("level").strip(),
        logger=logger_name,
        agent=agent,
        message=message,
        raw=safe_line,
        chapter_id=chapter_id,
    )


def read_logs(
    log_file: str | Path,
    *,
    level: str | None = None,
    agent: str | None = None,
    chapter: int | None = None,
    limit: int = 200,
) -> list[LogEntry]:
    """读取并过滤日志，返回最近 limit 条。"""
    path = Path(log_file)
    if not path.exists():
        return []
    entries = [parse_log_line(line) for line in path.read_text(encoding="utf-8", errors="replace").splitlines()]
    if level:
        entries = [entry for entry in entries if entry.level == level]
    if agent:
        entries = [entry for entry in entries if entry.agent == agent]
    if chapter is not None:
        entries = [entry for entry in entries if entry.chapter_id == chapter]
    return entries[-limit:]
