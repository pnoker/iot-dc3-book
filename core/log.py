"""
日志配置 —— 统一的结构化日志
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOG_FILE = "logs/book-writer.log"
DEFAULT_LOG_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_LOG_BACKUP_COUNT = 10


def setup_logging(
        level: str = "INFO",
        log_file: str | None = None,
        log_max_bytes: int = DEFAULT_LOG_MAX_BYTES,
        log_backup_count: int = DEFAULT_LOG_BACKUP_COUNT,
) -> logging.Logger:
    """
    配置全局日志。

    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        log_file: 日志文件路径，默认 logs/book-writer.log
        log_max_bytes: 单个日志文件最大字节数
        log_backup_count: 保留的历史日志文件数量

    Returns:
        根 logger
    """
    root = logging.getLogger("book_writer")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 避免重复添加 handler
    if root.handlers:
        return root

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    log_path = Path(log_file or DEFAULT_LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        str(log_path),
        maxBytes=log_max_bytes,
        backupCount=log_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    return root


def get_logger(name: str) -> logging.Logger:
    """获取子 logger"""
    return logging.getLogger(f"book_writer.{name}")
