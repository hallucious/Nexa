from __future__ import annotations

from typing import Any, Mapping, Sequence


def build_shell_section(*, headline: str, lines: Sequence[str] | None = None, detail_title: str, detail_items: Sequence[str] | None = None, controls: Sequence[Mapping[str, Any]] | None = None, history: Sequence[Mapping[str, Any]] | None = None, summary_empty: str | None = None, detail_empty: str | None = None) -> dict[str, Any]:
    summary_lines = [str(item) for item in (lines or ()) if isinstance(item, str) and item.strip()]
    detail_lines = [str(item) for item in (detail_items or ()) if isinstance(item, str) and item.strip()]
    summary = {
        "headline": headline,
        "lines": summary_lines or ([summary_empty] if isinstance(summary_empty, str) and summary_empty.strip() else []),
    }
    detail = {
        "title": detail_title,
        "items": detail_lines or ([detail_empty] if isinstance(detail_empty, str) and detail_empty.strip() else []),
    }
    payload: dict[str, Any] = {
        "summary": summary,
        "detail": detail,
        "controls": [dict(item) for item in (controls or ()) if isinstance(item, Mapping)],
    }
    if history is not None:
        payload["history"] = [dict(item) for item in history if isinstance(item, Mapping)]
    return payload
