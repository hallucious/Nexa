from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from src.providers.safe_mode import run_safe_mode, apply_safe_mode_prefix


@dataclass
class PerplexityProvider:
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
                {"role": "system", "content": "Return ONLY valid JSON. No markdown. No code fences."},
                {"role": "user", "content": prompt},
            ],
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
        }
        data = self._http_call(payload)
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
        return text, data

    @staticmethod
    def _clean_json_text(text: str) -> str:
        original = text.strip()

        # Remove markdown fences
        if original.startswith("```"):
            stripped = original.strip("`").strip()
            if stripped.lower().startswith("json"):
                stripped = stripped[4:].strip()
            original = stripped

        # Extract first balanced JSON object
        start = original.find("{")
        end = original.rfind("}")
        if start != -1 and end != -1 and end > start:
            original = original[start:end + 1]

        return original.strip()

    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 512,
    ) -> Tuple[str, Dict[str, Any], Optional[Exception]]:

        if not self.api_key:
            return "", {}, RuntimeError("PERPLEXITY_API_KEY is missing")

        try:
            def call_fn(p: str) -> str:
                t, raw = self._call(p, model=self.model, temperature=temperature, max_tokens=max_output_tokens)
                call_fn.last_raw = raw  # type: ignore
                return t

            call_fn.last_raw = {}

            res = run_safe_mode(apply_safe_mode_prefix(prompt), call_fn)
            raw = getattr(call_fn, "last_raw", {}) or {}
            return res.text, raw, None
        except Exception as e:
            return "", {}, e

    def verify(self, statement: str) -> Dict[str, Any]:
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

        raw_text = res.text.strip()
        cleaned = self._clean_json_text(raw_text)

        repair_applied = cleaned != raw_text
        format_status = "REPAIRED" if repair_applied else "CLEAN"

        try:
            obj = json.loads(cleaned)
        except Exception as e:
            format_status = "FAIL"
            g3_metrics = {
                "format_status": format_status,
                "content_status": "ERROR",
                "repair_applied": repair_applied,
                "parse_attempts": 1
            }
            raise RuntimeError(f"INVALID_REQUEST: Perplexity returned non-JSON: {raw_text[:200]}") from e

        if not isinstance(obj, dict):
            raise RuntimeError("INVALID_REQUEST: Perplexity JSON must be an object")

        verdict = obj.get("verdict", "ERROR")
        content_status = verdict if verdict in ("OK", "WARN", "ERROR") else "ERROR"

        g3_metrics = {
            "format_status": format_status,
            "content_status": content_status,
            "repair_applied": repair_applied,
            "parse_attempts": 1
        }

        obj["_g3_metrics"] = g3_metrics
        return obj
