from __future__ import annotations

import json
import os
import urllib.request

from src.providers.safe_mode import apply_safe_mode_text, split_into_chunks, safe_mode_reason
from typing import Any, Dict, List


class PerplexityProvider:
    """
    Minimal Perplexity API client.
    Purpose: evidence retrieval, not decision making.
    """

    API_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Perplexity API key is required")
        self.api_key = api_key

def _verify_once(self, statement: str, *, timeout_sec: int = 60) -> Dict[str, Any]:
    payload = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system",
                "content": apply_safe_mode_text(
                    "You are a fact-checking assistant. "
                    "Classify the statement as OK, WARN, or ERROR. "
                    "Provide a short justification and cite sources."
                ),
            },
            {"role": "user", "content": statement},
        ],
        "temperature": 0.0,
    }

    req = urllib.request.Request(
        url=self.API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        raw_bytes = resp.read()
        raw: Dict[str, Any] = json.loads(raw_bytes.decode("utf-8"))

    text = ""
    try:
        text = raw["choices"][0]["message"]["content"]
    except Exception:
        text = ""

    # Expect model to return JSON; parse defensively
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = {"verdict": "WARN", "confidence": 0.4, "citations": [], "summary": text[:500]}

    verdict = str(parsed.get("verdict", "WARN")).upper().strip()
    if verdict not in ("OK", "WARN", "ERROR"):
        verdict = "WARN"

    return {
        "verdict": verdict,
        "confidence": float(parsed.get("confidence", 0.5) or 0.5),
        "citations": parsed.get("citations", []) or [],
        "summary": str(parsed.get("summary", "") or ""),
        "raw": raw,
    }

def verify(self, statement: str) -> Dict[str, Any]:
    """Fact-check a statement. Lossless chunking on TOO_LONG."""
    statement = (statement or "").strip()
    reason = safe_mode_reason().upper()

    # Lossless preprocessing for TOO_LONG: chunk and aggregate worst verdict.
    if reason == "TOO_LONG" or len(statement) > 12000:
        chunks = split_into_chunks(statement, max_chars=3000)
        order = {"OK": 0, "WARN": 1, "ERROR": 2}
        worst = "OK"
        citations: List[Dict[str, str]] = []
        summaries: List[str] = []

        for i, ch in enumerate(chunks, start=1):
            r = self._verify_once(f"[CHUNK {i}/{len(chunks)}]
{ch}")
            v = str(r.get("verdict", "OK")).upper()
            if order.get(v, 0) > order.get(worst, 0):
                worst = v
            citations.extend((r.get("citations") or [])[:3])
            summaries.append(f"[{i}/{len(chunks)}] {r.get('summary','')}".strip())

        # de-dup citations by url
        seen = set()
        uniq = []
        for c in citations:
            u = (c or {}).get("url")
            if u and u not in seen:
                seen.add(u)
                uniq.append(c)

        return {
            "verdict": worst,
            "confidence": 0.5,
            "citations": uniq[:10],
            "summary": "
".join(summaries)[:2000],
        }

    # Normal path
    r = self._verify_once(statement)
    return {
        "verdict": r["verdict"],
        "confidence": r["confidence"],
        "citations": r["citations"],
        "summary": r["summary"],
    }
