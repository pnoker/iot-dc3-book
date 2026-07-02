from __future__ import annotations

from logging.handlers import RotatingFileHandler

from core.log import setup_logging


def test_setup_logging_uses_default_rotating_file(tmp_path, monkeypatch) -> None:
    import logging

    root = logging.getLogger("book_writer")
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    monkeypatch.chdir(tmp_path)

    logger = setup_logging()

    file_handlers = [handler for handler in logger.handlers if isinstance(handler, RotatingFileHandler)]
    assert len(file_handlers) == 1
    assert file_handlers[0].baseFilename.endswith("logs/book-writer.log")
    assert file_handlers[0].maxBytes == 10 * 1024 * 1024
    assert file_handlers[0].backupCount == 10
