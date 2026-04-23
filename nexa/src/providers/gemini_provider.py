from __future__ import annotations

import time
from src.providers.provider_adapter_contract import ProviderResult, make_failure, make_success, map_exception_to_reason_code
import json
import os
import urllib.request

from src.providers.env_diagnostics import resolve_api_key_or_raise
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from src.providers.safe_mode import run_safe_mode, apply_safe_mode_prefix


def _parse_optional_int(v: Optional[str]) -> Optional[int]:
    try:
        if v is None:
            return None
        s = str(v).strip()
        if s == "":
            return None
        return int(s)
    except Exception:
        return None


@dataclass
class GeminiResult:
    verdict: str  # "SAME" | "DRIFT" | "VIOLATION" | "UNKNOWN"
    rationale: str
    raw: Dict[str, Any]


class GeminiProvider:
    """Stdlib-only Gemini client (compat + SAFE_MODE v2).

    Compatibility guarantees (required by existing code/tests):
    - Exports GeminiResult
    - Provides judge_continuity(pic_text, current_text) -> GeminiResult
    - Provides generate_text(prompt=..., temperature=..., max_output_tokens=...) -> (text, raw, err)

    SAFE_MODE capabilities (provider-level):
    - TRANSIENT retries + optional fallback model
    - POLICY_REFUSAL guarded retry
    - INVALID_REQUEST format-guard retry
    - TOO_LONG chunk+aggregate (generic)
    """

    def __init__(self, api_key: str, *, model: str = "gemini-2.5-pro") -> None:
        self.api_key = (api_key or "").strip()
        self.model = (model or "gemini-2.5-pro").strip()
        self.fallback_model = (os.environ.get("GEMINI_FALLBACK_MODEL") or "").strip() or None
        self.thinking_budget = _parse_optional_int(os.environ.get("GEMINI_THINKING_BUDGET"))

    @staticmethod
    def from_env() -> "GeminiProvider":
        api_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
        if not api_key:
            api_key = (os.environ.get("GOOGLE_API_KEY") or "").strip()
        if not api_key:
            api_key = resolve_api_key_or_raise("GEMINI_API_KEY")
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
        return GeminiProvider(api_key, model=model)

    @staticmethod
    def from_api_key(api_key: str) -> "GeminiProvider":
        """Build from a directly-supplied API key (beginner / session path)."""
        return GeminiProvider(api_key)

    def judge_continuity(self, *, pic_text: str, current_text: str) -> GeminiResult:
        prompt = (
            "You are a strict reviewer for project semantic continuity.\n"
            "Given a Project Identity Contract (PIC) and the current design text, "
            "decide whether the current work is still the same project.\n\n"
            "Return ONLY valid JSON with keys: verdict, rationale.\n"
            "verdict must be one of: SAME, DRIFT, VIOLATION.\n\n"
            "=== PIC ===\n"
            f"{pic_text}\n\n"
            "=== CURRENT ===\n"
            f"{current_text}\n"
        )

        text, raw, err = self.generate_text(prompt=prompt, temperature=0.0, max_output_tokens=512)
        if err is not None:
            return GeminiResult(
                verdict="UNKNOWN",
                rationale=f"Gemini call failed: {type(err).__name__}: {err}",
                raw={"error": str(err)},
            )

        try:
            parsed = json.loads(text)
            verdict = str(parsed.get("verdict", "")).strip().upper()
            rationale = str(parsed.get("rationale", "")).strip()
            if verdict not in ("SAME", "DRIFT", "VIOLATION"):
                verdict = "UNKNOWN"
            return GeminiResult(verdict=verdict, rationale=rationale, raw={"api": raw, "model_text": text})
        except Exception as e:  # noqa: BLE001
            return GeminiResult(
                verdict="UNKNOWN",
                rationale=f"Could not parse JSON: {type(e).__name__}: {e}",
                raw={"api": raw, "model_text": text},
            )

    def _call_once(
        self,
        *,
        prompt: str,
        temperature: float,
        max_output_tokens: int,
        timeout_sec: int,
        model: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        if not self.api_key:
            raise RuntimeError(
            "[ERROR] GEMINI_API_KEY not found\n\n"
            "Fix:\n"
            "1. Create a .env file in project root\n"
            "2. Add:\n"
            "   GEMINI_API_KEY=your_key_here\n\n"
            "OR\n\n"
            "export GEMINI_API_KEY=your_key_here\n"
        )

        use_model = (model or self.model).strip()

        # Gemini 2.5 "thinking" tokens are billed/limited separately but still count
        # against maxOutputTokens in practice. If maxOutputTokens is too low, the model
        # may consume the entire budget on thinking and return no text parts.
        #
        # Strategy:
        # - If user configured GEMINI_THINKING_BUDGET, pass it through.
        # - Otherwise, for 2.5 Pro default to a conservative 128 thinking budget.
        # - Ensure maxOutputTokens is at least thinkingBudget + 64 (room for output).
        eff_thinking_budget: Optional[int] = self.thinking_budget
        if eff_thinking_budget is None and "gemini-2.5-pro" in use_model:
            eff_thinking_budget = 128

        eff_max_tokens = int(max_output_tokens)
        if eff_thinking_budget is not None:
            # Keep a small buffer so we actually get visible output.
            eff_max_tokens = max(eff_max_tokens, int(eff_thinking_budget) + 64)
        # Safety floor for 2.5 Pro; avoids empty outputs on trivial prompts.
        if "gemini-2.5-pro" in use_model:
            eff_max_tokens = max(eff_max_tokens, 256)

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{use_model}:generateContent?key={self.api_key}"
        )

        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": float(temperature),
                "maxOutputTokens": int(eff_max_tokens),
                **(
                    {"thinkingConfig": {"thinkingBudget": int(eff_thinking_budget)}}
                    if eff_thinking_budget is not None
                    else {}
                ),
            },
        }

        req = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                raw_bytes = resp.read()
        except Exception as e:  # noqa: BLE001
            # Let SAFE_MODE classify this
            raise RuntimeError(str(e)) from e

        raw_text = raw_bytes.decode("utf-8", errors="replace")
        raw = json.loads(raw_text)

        # Extract text (best-effort; Gemini returns candidates -> content -> parts).
        text_out = ""
        try:
            candidates = raw.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if isinstance(parts, list) and parts:
                    chunks = []
                    for pt in parts:
                        if isinstance(pt, dict) and "text" in pt and pt.get("text") is not None:
                            chunks.append(str(pt.get("text")))
                    text_out = "".join(chunks)
        except Exception:
            text_out = ""

        return text_out, raw
    def fingerprint(self) -> str:
        from src.providers.provider_adapter_contract import compute_provider_fingerprint

        info = {
            "provider": type(self).__name__,
            "api": "google.gemini.generateContent",
            "endpoint_base": "https://generativelanguage.googleapis.com/v1beta/models/<model>:generateContent",
            "model": self.model,
            "fallback_model": self.fallback_model,
            "thinking_budget": self.thinking_budget,
            "safe_mode": True,
        }
        return compute_provider_fingerprint(info)


    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 512,
        timeout_sec: int = 30,
    ) -> ProviderResult:
        """Return (text, raw_response, error).

        - If API key missing: returns ("", {}, Exception)
        - Otherwise uses SAFE_MODE v2 to retry/preprocess.
        """
        if not self.api_key:
            return "", {}, RuntimeError(
            "[ERROR] GEMINI_API_KEY not found\n\n"
            "Fix:\n"
            "1. Create a .env file in project root\n"
            "2. Add:\n"
            "   GEMINI_API_KEY=your_key_here\n\n"
            "OR\n\n"
            "export GEMINI_API_KEY=your_key_here\n"
        )

        def call_fn(p: str) -> str:
            # We only return text to SAFE_MODE; raw is captured separately via closure.
            t, _raw = self._call_once(
                prompt=p,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                timeout_sec=timeout_sec,
                model=self.model,
            )
            call_fn.last_raw = _raw  # type: ignore[attr-defined]
            return t

        call_fn.last_raw = {}  # type: ignore[attr-defined]

        fallback_fn = None
        if self.fallback_model:
            def fb(p: str) -> str:
                t, _raw = self._call_once(
                    prompt=p,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    timeout_sec=timeout_sec,
                    model=self.fallback_model,
                )
                fb.last_raw = _raw  # type: ignore[attr-defined]
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
            return make_failure(error=f"{type(e).__name__}: {e}", raw={}, reason_code=map_exception_to_reason_code(e), latency_ms=latency_ms)
