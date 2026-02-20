from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional, Tuple

import requests

from src.providers.safe_mode import apply_safe_mode_prefix
from src.providers.schema_utils import parse_json_object
from src.providers.result_models import PerplexityVerifyResult


class PerplexityProvider:
    """
    Minimal Perplexity Sonar API client (OpenAI-compatible Chat Completions).

    SaaS stability:
    - verify() returns a hybrid Mapping (PerplexityVerifyResult) so Gate code can use `.get(...)`
    - Best-effort JSON extraction
    - One retry on non-JSON / schema drift
    """

    API_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "sonar-pro",
        fallback_model: Optional[str] = None,
        timeout_sec: int = 40,
    ) -> None:
        api_key = (api_key or "").strip()
        if not api_key:
            raise ValueError("Perplexity API key is required")

        self.api_key = api_key
        self.model = (model or "sonar-pro").strip()
        self.fallback_model = (fallback_model or "").strip() or None
        self.timeout_sec = int(timeout_sec)

    @staticmethod
    def from_env() -> "PerplexityProvider":
        api_key = os.environ.get("PERPLEXITY_API_KEY", "") or os.environ.get("PPLX_API_KEY", "")
        model = os.environ.get("PERPLEXITY_MODEL", "sonar-pro")
        fb = os.environ.get("PERPLEXITY_FALLBACK_MODEL", "") or os.environ.get("PPLX_FALLBACK_MODEL", "")
        timeout = os.environ.get("PERPLEXITY_TIMEOUT_SEC", "") or os.environ.get("PPLX_TIMEOUT_SEC", "")
        timeout_i = int(timeout) if str(timeout).strip().isdigit() else 40
        return PerplexityProvider(api_key, model=model, fallback_model=(fb or None), timeout_sec=timeout_i)

    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 700,
        model_override: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any], Optional[Exception], Optional[int]]:
        """
        Returns: (text, raw_json, err, http_status)
        """
        safe_prompt = apply_safe_mode_prefix(prompt)

        payload = {
            "model": (model_override or self.model),
            "messages": [
                {"role": "system", "content": "You are a precise verifier. Follow formatting instructions exactly."},
                {"role": "user", "content": safe_prompt},
            ],
            "temperature": float(temperature),
            "max_tokens": int(max_output_tokens),
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        res = None
        try:
            res = requests.post(self.API_URL, headers=headers, json=payload, timeout=self.timeout_sec)
            status = int(res.status_code)
            res.raise_for_status()
            raw = res.json()
            text = ""
            try:
                text = raw.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
            except Exception:
                text = ""
            return text, raw, None, status
        except Exception as e:
            status = int(res.status_code) if res is not None and getattr(res, "status_code", None) is not None else None
            try:
                raw = res.json() if res is not None else {}
            except Exception:
                raw = {}
            return "", raw, e, status

    def verify(self, statement: str) -> PerplexityVerifyResult:
        """
        Gate3 contract expectation (dict-like):
          - verdict: PASS | FAIL | WARN | ERROR
          - confidence: optional float
          - citations: optional list[str]
          - summary: optional str
        """
        stmt = (statement or "").strip()
        if not stmt:
            return PerplexityVerifyResult(
                verdict="WARN",
                confidence=None,
                citations=[],
                summary="Empty statement; nothing to verify.",
                raw={"statement": statement},
            )

        schema_hint = (
            "Return ONLY a single JSON object (no markdown, no prose) matching:\n"
            "{\n"
            '  "verdict": "PASS" | "FAIL" | "WARN",\n'
            '  "confidence": number | null,\n'
            '  "summary": string,\n'
            '  "citations": [string]\n'
            "}\n"
        )

        prompt = (
            f"{schema_hint}\n"
            "Task: verify the factual correctness of the following statement. "
            "If it is unverifiable or ambiguous, use WARN.\n\n"
            f"STATEMENT:\n{stmt}\n"
        )

        text, raw, err, status = self.generate_text(prompt=prompt, temperature=0.0, max_output_tokens=700)

        # Auth errors should surface clearly for Gate3 categorization.
        if status == 401:
            raise RuntimeError("INVALID_REQUEST: Perplexity 401 Unauthorized (check PERPLEXITY_API_KEY).")

        if err is not None and not text:
            # For transient network/server errors, raise with a recognizable prefix for Gate3
            raise RuntimeError(f"TRANSIENT_ERROR: Perplexity call failed: {type(err).__name__}: {err}")

        parsed = parse_json_object(text)

        # One retry if not JSON or missing required keys
        def _looks_valid(p: Optional[dict]) -> bool:
            if not isinstance(p, dict):
                return False
            return "verdict" in p and "summary" in p and "citations" in p

        if not _looks_valid(parsed):
            retry_prompt = (
                f"{schema_hint}\n"
                "Your previous response was not valid JSON or did not match the schema. "
                "Respond again with JSON only, exactly matching the schema.\n\n"
                f"STATEMENT:\n{stmt}\n"
            )
            time.sleep(0.25)
            text2, raw2, err2, status2 = self.generate_text(prompt=retry_prompt, temperature=0.0, max_output_tokens=700)
            raw = {"first": raw, "second": raw2}
            if status2 == 401:
                raise RuntimeError("INVALID_REQUEST: Perplexity 401 Unauthorized (check PERPLEXITY_API_KEY).")
            if err2 is not None and not text2:
                raise RuntimeError(f"TRANSIENT_ERROR: Perplexity retry failed: {type(err2).__name__}: {err2}")
            parsed = parse_json_object(text2)

        if not _looks_valid(parsed):
            # Keep Gate3 behavior deterministic: invalid provider output => INVALID_REQUEST
            raise RuntimeError("INVALID_REQUEST: Perplexity returned non-JSON or schema-invalid response.")

        verdict = str(parsed.get("verdict", "WARN")).strip().upper()
        if verdict not in {"PASS", "FAIL", "WARN"}:
            verdict = "WARN"

        confidence = parsed.get("confidence", None)
        try:
            confidence = float(confidence) if confidence is not None else None
        except Exception:
            confidence = None

        citations = parsed.get("citations", [])
        if citations is None:
            citations = []
        if not isinstance(citations, list):
            citations = [str(citations)]
        citations = [str(x) for x in citations]

        summary = str(parsed.get("summary", "") or "").strip()

        return PerplexityVerifyResult(
            verdict=verdict,
            confidence=confidence,
            citations=citations,
            summary=summary,
            raw={"api": raw, "model_text": text, "parsed": parsed, "statement": stmt},
        )
