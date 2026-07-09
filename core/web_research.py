"""轻量在线资料抓取，用于把显式 URL 转成证据摘录。"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from core.log import get_logger

logger = get_logger("web_research")

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.I | re.S)
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class WebEvidence:
    """在线资料证据摘录。"""

    url: str
    title: str
    excerpt: str


def fetch_web_evidence(urls: list[str], timeout_seconds: float, max_chars_per_url: int) -> list[WebEvidence]:
    """抓取显式配置的 URL 并提取可放入资料包的文本摘录。"""
    evidence: list[WebEvidence] = []
    for url in urls:
        if not _is_http_url(url):
            raise ValueError(f"在线资料 URL 必须是 HTTP(S): {url}")
        try:
            evidence.append(_fetch_one(url, timeout_seconds, max_chars_per_url))
        except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError) as exc:
            logger.error("在线资料抓取失败: %s", url, exc_info=True)
            raise RuntimeError(f"在线资料抓取失败: {url}") from exc
    return evidence


def _fetch_one(url: str, timeout_seconds: float, max_chars: int) -> WebEvidence:
    request = Request(url, headers={"User-Agent": "mi-book-writer/0.1"})
    with urlopen(request, timeout=timeout_seconds) as response:
        content_type = response.headers.get("content-type", "")
        charset = _extract_charset(content_type) or "utf-8"
        body = response.read(max(max_chars * 20, 65536)).decode(charset, errors="replace")
    title = _extract_title(body) or urlparse(url).netloc
    text = _html_to_text(body) if "html" in content_type.lower() or "<html" in body[:500].lower() else body
    return WebEvidence(url=url, title=title, excerpt=text[:max_chars].strip())


def _is_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _extract_charset(content_type: str) -> str:
    match = re.search(r"charset=([\w-]+)", content_type, re.I)
    return match.group(1) if match else ""


def _extract_title(body: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    return _normalize_text(match.group(1)) if match else ""


def _html_to_text(body: str) -> str:
    body = _SCRIPT_STYLE_RE.sub(" ", body)
    body = _TAG_RE.sub(" ", body)
    return _normalize_text(html.unescape(body))


def _normalize_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()
