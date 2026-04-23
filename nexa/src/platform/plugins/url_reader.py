from __future__ import annotations

from typing import Any
from urllib.parse import urlparse
import urllib.request


def fetch_url_text(url: str, *, timeout_sec: int = 15) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"unsupported URL scheme: {parsed.scheme or 'unknown'}")

    request = urllib.request.Request(
        url=url,
        headers={"User-Agent": "NexaUrlReader/1.0"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        payload = response.read()
        content_type = response.headers.get_content_charset() if hasattr(response.headers, 'get_content_charset') else None
        encoding = content_type or "utf-8"
        return payload.decode(encoding, errors="replace")


def read_url_plugin(*, url: str, timeout_sec: int = 15, **_: Any) -> dict[str, Any]:
    text = fetch_url_text(url, timeout_sec=timeout_sec)
    return {
        "text": text,
        "source_type": "url",
        "url": url,
    }


PLUGINS = {
    "nexa.url_reader": {
        "callable": read_url_plugin,
        "version": "1.0.0",
        "description": "Fetch a URL as text into Nexa input context.",
    }
}
