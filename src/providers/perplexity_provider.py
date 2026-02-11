from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any, Dict, List, Optional

from src.providers.safe_mode import run_safe_mode


class PerplexityProvider:
    """Minimal Perplexity API client (evidence retrieval).

    SAFE_MODE support:
    - TRANSIENT retries
    - TOO_LONG chunk+aggregate for long statements
    - POLICY/INVALID_REQUEST guarded retries (best-effort)
    """

    API_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(self, api_key: str, *, model: str = "sonar-pro", fallback_model: Optional[str] = None):
        if not api_key:
            raise ValueError("Perplexity API key is required")
        self.api_key = api_key
        self.model = model
        self.fallback_model = fallback_model or os.environ.get("PPLX_FALLBACK_MODEL")

    def _http_call(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.API_URL,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw)

    def _call(self, prompt: str, *, model: Optional[str] = None) -> str:
        payload = {
            "model": model or self.model,
            "messages": [
                {"role": "system", "content": "You are a rigorous evidence checker. Return concise JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        data = self._http_call(payload)
        # Perplexity returns choices[0].message.content
        return data["choices"][0]["message"]["content"]

    def verify(self, statement: str) -> Dict[str, Any]:
        """Verify a statement. Returns dict with verdict/confidence/citations/summary."""

        def build_prompt(s: str) -> str:
            return (
                "Verify the following statement using web evidence.\n"
                "Return ONLY valid JSON with keys: verdict(OK|WARN|ERROR), confidence(0-1), citations(list), summary.\n\n"
                f"STATEMENT:\n{s}"
            )

        def call_fn(p: str) -> str:
            return self._call(p, model=self.model)

        fallback_fn = None
        if self.fallback_model:
            def fb(p: str) -> str:
                return self._call(p, model=self.fallback_model)
            fallback_fn = fb

        res = run_safe_mode(build_prompt(statement), call_fn, fallback_call_fn=fallback_fn)
        # Parse JSON (best-effort). If it fails, raise INVALID_REQUEST-like error to trigger caller handling.
        try:
            obj = json.loads(res.text)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"INVALID_REQUEST: Perplexity returned non-JSON: {res.text[:200]}") from e

        # Normalize citations
        if "citations" in obj and isinstance(obj["citations"], list):
            norm: List[Dict[str, str]] = []
            for c in obj["citations"]:
                if isinstance(c, dict):
                    title = str(c.get("title", ""))
                    url = str(c.get("url", ""))
                    norm.append({"title": title, "url": url})
            obj["citations"] = norm

        return obj
