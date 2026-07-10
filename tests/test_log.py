from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from rich.highlighter import NullHighlighter
from rich.logging import RichHandler

from core.log import CONSOLE_LOG_FORMAT, FILE_LOG_FORMAT, setup_logging


def _reset_book_writer_logger() -> None:
    logger = logging.getLogger("book_writer")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def test_setup_logging_uses_default_rotating_file(tmp_path, monkeypatch) -> None:
    _reset_book_writer_logger()
    monkeypatch.chdir(tmp_path)

    logger = setup_logging()

    rich_handlers = [handler for handler in logger.handlers if isinstance(handler, RichHandler)]
    file_handlers = [handler for handler in logger.handlers if isinstance(handler, RotatingFileHandler)]
    assert len(rich_handlers) == 1
    assert len(file_handlers) == 1
    assert rich_handlers[0].formatter is not None
    assert rich_handlers[0].formatter._fmt == CONSOLE_LOG_FORMAT
    assert rich_handlers[0].console.stderr is True
    assert isinstance(rich_handlers[0].highlighter, NullHighlighter)
    assert rich_handlers[0].markup is False
    assert rich_handlers[0].rich_tracebacks is False
    assert rich_handlers[0].enable_link_path is False
    assert file_handlers[0].formatter is not None
    assert file_handlers[0].formatter._fmt == FILE_LOG_FORMAT
    assert file_handlers[0].baseFilename.endswith("logs/book-writer.log")
    assert file_handlers[0].maxBytes == 10 * 1024 * 1024
    assert file_handlers[0].backupCount == 10
    assert logger.propagate is False


def test_setup_logging_reconfigures_without_duplicate_handlers(tmp_path) -> None:
    _reset_book_writer_logger()

    setup_logging(level="DEBUG", log_file=str(tmp_path / "first.log"))
    logger = setup_logging(level="WARNING", log_file=str(tmp_path / "second.log"))

    rich_handlers = [handler for handler in logger.handlers if isinstance(handler, RichHandler)]
    file_handlers = [handler for handler in logger.handlers if isinstance(handler, RotatingFileHandler)]
    assert len(logger.handlers) == 2
    assert len(rich_handlers) == 1
    assert len(file_handlers) == 1
    assert logger.level == logging.WARNING
    assert rich_handlers[0].level == logging.WARNING
    assert file_handlers[0].level == logging.WARNING
    assert file_handlers[0].baseFilename.endswith("second.log")
