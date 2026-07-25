"""
日志配置 —— 统一的结构化日志
"""

from __future__ import annotations

import logging
from logging.config import dictConfig
from pathlib import Path

from rich.console import Console
from rich.highlighter import NullHighlighter

DEFAULT_LOG_FILE = "logs/book-builder.log"
DEFAULT_LOG_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_LOG_BACKUP_COUNT = 10
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
FILE_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
CONSOLE_LOG_FORMAT = "%(message)s"


def setup_logging(
        level: str = "INFO",
        log_file: str | None = None,
        log_max_bytes: int = DEFAULT_LOG_MAX_BYTES,
        log_backup_count: int = DEFAULT_LOG_BACKUP_COUNT,
) -> logging.Logger:
    """配置全局日志。"""
    log_path = Path(log_file or DEFAULT_LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_level = level.upper()

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "console": {"format": CONSOLE_LOG_FORMAT, "datefmt": LOG_DATE_FORMAT},
                "file": {"format": FILE_LOG_FORMAT, "datefmt": LOG_DATE_FORMAT},
            },
            "handlers": {
                "console": {
                    "class": "rich.logging.RichHandler",
                    "level": log_level,
                    "formatter": "console",
                    "console": Console(stderr=True, markup=False, highlight=False),
                    "highlighter": NullHighlighter(),
                    "markup": False,
                    "rich_tracebacks": False,
                    "show_path": True,
                    "enable_link_path": False,
                    "log_time_format": LOG_DATE_FORMAT,
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": log_level,
                    "formatter": "file",
                    "filename": str(log_path),
                    "maxBytes": log_max_bytes,
                    "backupCount": log_backup_count,
                    "encoding": "utf-8",
                },
            },
            "loggers": {
                "book_builder": {
                    "level": log_level,
                    "handlers": ["console", "file"],
                    "propagate": False,
                }
            },
        }
    )

    return logging.getLogger("book_builder")


def get_logger(name: str) -> logging.Logger:
    """获取子 logger"""
    return logging.getLogger(f"book_builder.{name}")
