from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional, Tuple

from src.providers.provider_contract import (
    ProviderResult,
    make_failure,
    make_success,
    map_exception_to_reason_code,
    compute_provider_fingerprint,
)
from src.providers.safe_mode import apply_safe_mode_prefix, run_safe_mode


class ClaudeProvider:
    """Stdlib-only Anthropic Claude client (AI-PROVIDER v1.1.0).

    Design constraints:
    - Matches other provider modules: generate_text(prompt=..., temperature=..., max_output_tokens=...) -> ProviderResult
    - SAFE_MODE v2 integrated via src.providers.safe_mode
    - No secrets in raw/error/fingerprint
    """

    API_URL = "https://api.anthropic.com/v1/messages"
    ANTHROPIC_VERSION = "2023-06-01"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(self, api_key: str, *, model: str = DEFAULT_MODEL, timeout_sec: int = 60) -> None:
        self.api_key = (api_key or "").strip()
        self.model = (model or self.DEFAULT_MODEL).strip()
        self.timeout_sec = int(timeout_sec)

    @classmethod
    def from_env(cls) -> "ClaudeProvider":
        api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is missing")
        model = (os.environ.get("ANTHROPIC_MODEL") or cls.DEFAULT_MODEL).strip()
        timeout = (os.environ.get("ANTHROPIC_TIMEOUT_SEC") or "").strip()
        timeout_i = int(timeout) if timeout.isdigit() else 60
        return cls(api_key, model=model, timeout_sec=timeout_i)

    def fingerprint(self) -> str:
        info = {
            "provider": type(self).__name__,
            "api": "anthropic.messages",
            "endpoint": self.API_URL,
            "anthropic_version": self.ANTHROPIC_VERSION,
            "model": self.model,
            "timeout_sec": self.timeout_sec,
            "safe_mode": True,
        }
        return compute_provider_fingerprint(info)

    def _http_call(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        import urllib.request

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.API_URL,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": self.ANTHROPIC_VERSION,
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
            raw_bytes = resp.read()
        raw_text = raw_bytes.decode("utf-8", errors="replace")
        return json.loads(raw_text)

    @staticmethod
    def _extract_text(raw: Dict[str, Any]) -> str:
        # Anthropic Messages API: content is a list; each item may have type and text.
        parts = []
        for item in (raw.get("content") or []):
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join([p for p in parts if p.strip()]).strip()

    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
    ) -> ProviderResult:
        if not self.api_key:
            return make_failure(
                error="ANTHROPIC_API_KEY is missing",
                raw={},
                reason_code="INVALID_REQUEST",
                latency_ms=0,
            )

        safe_prompt = apply_safe_mode_prefix(prompt or "")

        payload: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": int(max_output_tokens),
            "messages": [{"role": "user", "content": safe_prompt}],
            "temperature": float(temperature),
        }

        latency_ms = 0
        try:
            start = time.perf_counter()

            def _call() -> Tuple[str, Dict[str, Any]]:
                raw = self._http_call(payload)
                text = self._extract_text(raw)
                return text, raw

            text, raw = run_safe_mode(_call)
            latency_ms = int((time.perf_counter() - start) * 1000.0)

            tokens_used = None
            try:
                tokens_used = (raw.get("usage") or {}).get("output_tokens")
            except Exception:
                tokens_used = None

            return make_success(text=text, raw=raw, latency_ms=latency_ms, tokens_used=tokens_used)
        except Exception as e:
            return make_failure(
                error=f"{type(e).__name__}: {e}",
                raw={},
                reason_code=map_exception_to_reason_code(e),
                latency_ms=latency_ms,
            )
