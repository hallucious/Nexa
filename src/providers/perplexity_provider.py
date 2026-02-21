from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from src.providers.safe_mode import run_safe_mode, apply_safe_mode_prefix


@dataclass
class PerplexityProvider:
    """Minimal Perplexity Sonar API client (OpenAI-compatible Chat Completions).

    Public API (used by gates/tests):
      - from_env() -> PerplexityProvider
      - generate_text(prompt=..., temperature=..., max_output_tokens=...) -> (text, raw, err)
      - verify(statement) -> dict(verdict, confidence, citations, summary)

    Notes
    - Stdlib-only (urllib). No requests dependency.
    - SAFE_MODE is applied in generate_text and verify (except for A3 fault injection bypass cases).
    """

    api_key: str
    model: str = "sonar-pro"
    fallback_model: Optional[str] = None
    timeout_sec: int = 45

    API_URL: str = "https://api.perplexity.ai/chat/completions"

    @classmethod
    def from_env(cls) -> "PerplexityProvider":
        api_key = (os.environ.get("PERPLEXITY_API_KEY") or os.environ.get("PPLX_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("INVALID_REQUEST: PERPLEXITY_API_KEY is missing")
        model = (os.environ.get("PERPLEXITY_MODEL") or "sonar-pro").strip()
        fb = (os.environ.get("PERPLEXITY_FALLBACK_MODEL") or os.environ.get("PPLX_FALLBACK_MODEL") or "").strip() or None
        timeout = (os.environ.get("PERPLEXITY_TIMEOUT_SEC") or os.environ.get("PPLX_TIMEOUT_SEC") or "").strip()
        timeout_i = int(timeout) if timeout.isdigit() else 45
        return cls(api_key=api_key, model=model, fallback_model=fb, timeout_sec=timeout_i)

    # --------------------------
    # A3 fault injection helpers
    # --------------------------
    @staticmethod
    def _fault_mode() -> str:
        return (os.environ.get("PPLX_FAULT_MODE") or os.environ.get("PERPLEXITY_FAULT_MODE") or "").strip().upper()

    @classmethod
    def _apply_fault_injection_call_level(cls) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Fault injection for call-level APIs (generate_text).

        Returns:
          - None if no fault injection requested.
          - (text, raw) for simulated success-like responses (e.g., NON_JSON)
        Raises:
          - RuntimeError with category=... markers for simulated failures.
        """
        fm = cls._fault_mode()
        if not fm:
            return None

        if fm in ("RATE_LIMIT_429", "429", "RATE_LIMIT"):
            raise RuntimeError("category=TRANSIENT_ERROR code=429 message=Too Many Requests (simulated)")
        if fm in ("TIMEOUT", "TIMEOUT_ERROR"):
            raise RuntimeError("category=TRANSIENT_ERROR message=Timeout (simulated)")
        if fm in ("NON_JSON", "NONJSON"):
            return ("THIS IS NOT JSON (simulated)", {"simulated": True, "fault_mode": fm})
        # AUTH and SCHEMA_INVALID are handled at verify() level (bypass SAFE_MODE) for determinism.
        return None

    @classmethod
    def _apply_fault_injection_verify_bypass(cls) -> None:
        """Fault injection that must bypass SAFE_MODE to keep error shape deterministic."""
        fm = cls._fault_mode()
        if not fm:
            return

        if fm.startswith("AUTH") or fm in ("AUTH_401", "401", "UNAUTHORIZED", "AUTH_403", "403", "FORBIDDEN"):
            code = "403" if ("403" in fm or fm in ("AUTH_403", "403", "FORBIDDEN")) else "401"
            msg = "Unauthorized" if code == "401" else "Forbidden"
            raise RuntimeError(f"category=HARD_ERROR code={code} message={msg} (simulated via {fm})")

        if fm in ("SCHEMA_INVALID", "SCHEMA"):
            raise RuntimeError(f"category=UNKNOWN_ERROR code=SCHEMA_INVALID message=Schema invalid (simulated via {fm})")

    # --------------------------
    # HTTP + parsing
    # --------------------------
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

    def _call(self, prompt: str, *, model: Optional[str], temperature: float, max_tokens: int) -> Tuple[str, Dict[str, Any]]:
        payload: Dict[str, Any] = {
            "model": (model or self.model),
            "messages": [
                {"role": "system", "content": "You are a rigorous evidence checker. Return concise JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
        }
        data = self._http_call(payload)
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
        return text, data

    # --------------------------
    # Public APIs
    # --------------------------
    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 512,
    ) -> Tuple[str, Dict[str, Any], Optional[Exception]]:
        """Return (text, raw_response, error). Never raises."""
        if not self.api_key:
            return "", {}, RuntimeError("PERPLEXITY_API_KEY is missing")

        try:
            sim = self._apply_fault_injection_call_level()
            if sim is not None:
                text, raw = sim
                return text, raw, None

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

            res = run_safe_mode(apply_safe_mode_prefix(prompt), call_fn, fallback_call_fn=fallback_fn)
            raw = getattr(call_fn, "last_raw", {}) or {}
            if fallback_fn is not None and res.stage.startswith("FALLBACK"):
                raw = getattr(fallback_fn, "last_raw", {}) or {}
            return res.text, raw, None
        except Exception as e:  # noqa: BLE001
            return "", {}, e

    def verify(self, statement: str) -> Dict[str, Any]:
        """Verify a statement. Returns dict with verdict/confidence/citations/summary.

        Raises RuntimeError on failures. Gate3 decides whether to STOP/PASS/FAIL.
        """
        # A3 fault injection: bypass SAFE_MODE for deterministic auth/schema behavior.
        self._apply_fault_injection_verify_bypass()

        def build_prompt(s: str) -> str:
            return (
                "Verify the following statement using web evidence.\n"
                "Return ONLY valid JSON with keys: verdict(OK|WARN|ERROR), confidence(0-1), citations(list), summary.\n\n"
                f"STATEMENT:\n{s}"
            )

        def call_fn(p: str) -> str:
            text, _, err = self.generate_text(prompt=p, temperature=0.0, max_output_tokens=512)
            if err:
                raise err
            return text

        res = run_safe_mode(build_prompt(statement), call_fn)

        try:
            obj = json.loads(res.text)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"INVALID_REQUEST: Perplexity returned non-JSON: {res.text[:200]}") from e

        # Minimal normalization (keep dict contract stable)
        if not isinstance(obj, dict):
            raise RuntimeError(f"INVALID_REQUEST: Perplexity JSON must be an object, got {type(obj).__name__}")

        obj.setdefault("verdict", "ERROR")
        obj.setdefault("confidence", 0.0)
        obj.setdefault("citations", [])
        obj.setdefault("summary", "")
        return obj
