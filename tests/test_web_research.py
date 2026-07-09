from __future__ import annotations

from urllib.error import URLError

import pytest

from core.web_research import fetch_web_evidence


def test_fetch_web_evidence_rejects_non_http_url() -> None:
    with pytest.raises(ValueError, match=r"HTTP\(S\)"):
        fetch_web_evidence(["file:///tmp/report.html"], timeout_seconds=1, max_chars_per_url=100)


def test_fetch_web_evidence_raises_on_fetch_error(monkeypatch) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise URLError("offline")

    monkeypatch.setattr("core.web_research.urlopen", fail)

    with pytest.raises(RuntimeError, match="在线资料抓取失败"):
        fetch_web_evidence(["https://example.test/report"], timeout_seconds=1, max_chars_per_url=100)
