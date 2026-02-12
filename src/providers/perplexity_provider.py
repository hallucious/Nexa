from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from src.providers.safe_mode import run_safe_mode, apply_safe_mode_prefix


class PerplexityProvider:
    """Minimal Perplexity Sonar API client (OpenAI-compatible Chat Completions).

    Compatibility guarantees (required by existing pipeline code/tests):
    - Provides generate_text(prompt=..., temperature=..., max_output_tokens=...) -> (text, raw, err)
    - Provides from_env() constructor
    - Keeps verify(statement) helper for evidence-checking use cases

    SAFE_MODE support (provider-level):
    - TRANSIENT retries
    - TOO_LONG chunk+aggregate
    - POLICY/INVALID_REQUEST guarded retries (best-effort)
    """

    API_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "sonar-pro",
        fallback_model: Optional[str] = None,
        timeout_sec: int = 60,
    ) -> None:
        if not (api_key or "").strip():
            raise ValueError("Perplexity API key is required")
        self.api_key = api_key.strip()
        self.model = (model or "sonar-pro").strip()
        self.fallback_model = (fallback_model or os.environ.get("PERPLEXITY_FALLBACK_MODEL") or os.environ.get("PPLX_FALLBACK_MODEL") or "").strip() or None
        self.timeout_sec = int(timeout_sec)

    @staticmethod
    def from_env() -> "PerplexityProvider":
        api_key = os.environ.get("PERPLEXITY_API_KEY", "") or os.environ.get("PPLX_API_KEY", "")
        model = os.environ.get("PERPLEXITY_MODEL", "sonar-pro")
        fb = os.environ.get("PERPLEXITY_FALLBACK_MODEL", "") or os.environ.get("PPLX_FALLBACK_MODEL", "")
        timeout = os.environ.get("PERPLEXITY_TIMEOUT_SEC", "") or os.environ.get("PPLX_TIMEOUT_SEC", "")
        try:
            timeout_i = int(timeout) if str(timeout).strip() else 60
        except Exception:
            timeout_i = 60
        return PerplexityProvider(api_key, model=model, fallback_model=(fb or None), timeout_sec=timeout_i)

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
        with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)

    def _call(self, prompt: str, *, model: Optional[str] = None, temperature: float = 0.2, max_tokens: Optional[int] = None) -> Tuple[str, Dict[str, Any]]:
        payload: Dict[str, Any] = {
            "model": (model or self.model),
            "messages": [
                {"role": "system", "content": "You are a rigorous evidence checker. Return concise JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": float(temperature),
        }
        # Perplexity Sonar follows OpenAI Chat Completions; use max_tokens when provided.
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)

        data = self._http_call(payload)
        # Perplexity returns choices[0].message.content
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
        return text, data

    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 512,
    ) -> Tuple[str, Dict[str, Any], Optional[Exception]]:
        """Return (text, raw_response, error)."""
        if not self.api_key:
            return "", {}, RuntimeError("PERPLEXITY_API_KEY is missing")

        def call_fn(p: str) -> str:
            t, raw = self._call(p, model=self.model, temperature=temperature, max_tokens=max_output_tokens)
            call_fn.last_raw = raw  # type: ignore[attr-defined]
            return t

        call_fn.last_raw = {}  # type: ignore[attr-defined]

        fallback_fn = None
        if self.fallback_model:

            def fb(p: str) -> str:
                t, raw = self._call(p, model=self.fallback_model, temperature=temperature, max_tokens=max_output_tokens)
                fb.last_raw = raw  # type: ignore[attr-defined]
                return t

            fb.last_raw = {}  # type: ignore[attr-defined]
            fallback_fn = fb

        try:
            res = run_safe_mode(apply_safe_mode_prefix(prompt), call_fn, fallback_call_fn=fallback_fn)
            raw = getattr(call_fn, "last_raw", {}) or {}
            if fallback_fn is not None and res.stage.startswith("FALLBACK"):
                raw = getattr(fallback_fn, "last_raw", {}) or {}
            return res.text, raw, None
        except Exception as e:  # noqa: BLE001
            return "", {}, e

    def verify(self, statement: str) -> Dict[str, Any]:
        """Verify a statement. Returns dict with verdict/confidence/citations/summary."""

        def build_prompt(s: str) -> str:
            return (
                "Verify the following statement using web evidence.\n"
                "Return ONLY valid JSON with keys: verdict(OK|WARN|ERROR), confidence(0-1), citations(list), summary.\n\n"
                f"STATEMENT:\n{s}"
            )

        def call_fn(p: str) -> str:
            t, raw = self._call(p, model=self.model, temperature=0.2, max_tokens=512)
            call_fn.last_raw = raw  # type: ignore[attr-defined]
            return t

        call_fn.last_raw = {}  # type: ignore[attr-defined]

        fallback_fn = None
        if self.fallback_model:

            def fb(p: str) -> str:
                t, raw = self._call(p, model=self.fallback_model, temperature=0.2, max_tokens=512)
                fb.last_raw = raw  # type: ignore[attr-defined]
                return t

            fb.last_raw = {}  # type: ignore[attr-defined]
            fallback_fn = fb

        res = run_safe_mode(build_prompt(statement), call_fn, fallback_call_fn=fallback_fn)

        try:
            obj = json.loads(res.text)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"INVALID_REQUEST: Perplexity returned non-JSON: {res.text[:200]}") from e

        # Normalize citations (best-effort)
        if "citations" in obj and isinstance(obj["citations"], list):
            norm: List[Dict[str, str]] = []
            for c in obj["citations"]:
                if isinstance(c, dict):
                    title = str(c.get("title", ""))
                    url = str(c.get("url", ""))
                    norm.append({"title": title, "url": url})
                elif isinstance(c, str):
                    norm.append({"title": "", "url": c})
            obj["citations"] = norm

        return obj
