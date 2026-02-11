from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, Optional, Tuple

from src.providers.safe_mode import run_safe_mode, apply_safe_mode_prefix


class OpenAIProvider:
    """Stdlib-only OpenAI client (SAFE_MODE v2).

    Compatibility goals:
    - from_env() constructor
    - generate(prompt)->str convenience
    - generate_text(prompt, temperature=..., max_output_tokens=..., model=...) -> (text, raw, err)

    NOTE:
    - This implementation uses the OpenAI Responses API via HTTPS (no third-party SDK).
    - Set OPENAI_API_KEY in .env (loaded by your env loader).
    """

    API_URL = "https://api.openai.com/v1/responses"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gpt-4.1",
        fallback_model: Optional[str] = None,
        timeout_s: int = 60,
    ) -> None:
        self.api_key = (api_key or "").strip()
        if not self.api_key:
            raise ValueError("OpenAI API key is required (OPENAI_API_KEY)")
        self.model = (model or "gpt-4.1").strip()
        self.fallback_model = (fallback_model or os.environ.get("OPENAI_FALLBACK_MODEL") or "").strip() or None
        self.timeout_s = int(timeout_s)

    @staticmethod
    def from_env() -> "OpenAIProvider":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        model = os.environ.get("OPENAI_MODEL", "gpt-4.1")
        fallback_model = os.environ.get("OPENAI_FALLBACK_MODEL")
        timeout_s = int(os.environ.get("OPENAI_TIMEOUT_S", "60"))
        return OpenAIProvider(api_key, model=model, fallback_model=fallback_model, timeout_s=timeout_s)

    def _extract_text(self, raw: Dict[str, Any]) -> str:
        # Preferred: Responses API provides `output_text` in many SDKs; sometimes in JSON too.
        if isinstance(raw, dict):
            if isinstance(raw.get("output_text"), str) and raw["output_text"].strip():
                return raw["output_text"].strip()

            # Try to parse `output` blocks (Responses API format)
            out = raw.get("output")
            if isinstance(out, list):
                parts = []
                for item in out:
                    if not isinstance(item, dict):
                        continue
                    content = item.get("content")
                    if isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and c.get("type") == "output_text":
                                t = c.get("text")
                                if isinstance(t, str) and t:
                                    parts.append(t)
                if parts:
                    return "\n".join(parts).strip()

        # Fallback: stringify
        return json.dumps(raw, ensure_ascii=False)

    def _http_call(
        self,
        *,
        prompt: str,
        model: str,
        temperature: float = 0.0,
        max_output_tokens: int = 2048,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": model,
            "input": prompt,
            "temperature": float(temperature),
            "max_output_tokens": int(max_output_tokens),
        }
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
        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        return json.loads(body)

    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 2048,
        model: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any], Optional[str]]:
        """Return (text, raw, err). err is a short string or None."""

        prompt2 = apply_safe_mode_prefix(prompt)

        def call_fn(p: str) -> str:
            raw = self._http_call(
                prompt=p,
                model=model or self.model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            # stash last raw in closure via attribute
            call_fn._last_raw = raw  # type: ignore[attr-defined]
            return self._extract_text(raw)

        def fallback_call_fn(p: str) -> str:
            if not self.fallback_model:
                raise RuntimeError("No fallback model configured")
            raw = self._http_call(
                prompt=p,
                model=self.fallback_model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            fallback_call_fn._last_raw = raw  # type: ignore[attr-defined]
            return self._extract_text(raw)

        try:
            res = run_safe_mode(
                prompt2,
                call_fn,
                fallback_call_fn=fallback_call_fn if self.fallback_model else None,
            )
            raw: Dict[str, Any] = getattr(call_fn, "_last_raw", {})  # type: ignore[attr-defined]
            # If fallback used, prefer its raw if present.
            raw_fb: Dict[str, Any] = getattr(fallback_call_fn, "_last_raw", {})  # type: ignore[attr-defined]
            if raw_fb:
                raw = raw_fb
            return res.text, raw, None
        except Exception as e:
            return "", {}, f"{type(e).__name__}: {e}"

    def generate(self, prompt: str) -> str:
        text, _raw, err = self.generate_text(prompt=prompt)
        if err:
            raise RuntimeError(err)
        return text
