
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

    @staticmethod
    def _fault_mode() -> str:
        return (os.environ.get("PPLX_FAULT_MODE") or os.environ.get("PERPLEXITY_FAULT_MODE") or "").strip().upper()

    @classmethod
    def _apply_fault_injection_verify_bypass(cls) -> None:
        fm = cls._fault_mode()
        if not fm:
            return

        if fm.startswith("AUTH") or fm in ("AUTH_401", "401", "UNAUTHORIZED", "AUTH_403", "403", "FORBIDDEN"):
            code = "403" if ("403" in fm or fm in ("AUTH_403", "403", "FORBIDDEN")) else "401"
            msg = "Unauthorized" if code == "401" else "Forbidden"
            raise RuntimeError(f"category=HARD_ERROR code={code} message={msg} (simulated via {fm})")

        if fm in ("SCHEMA_INVALID", "SCHEMA"):
            raise RuntimeError(f"category=UNKNOWN_ERROR code=SCHEMA_INVALID message=Schema invalid (simulated via {fm})")

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
        text = text.strip()

        # Remove markdown fences
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()

        # Extract first balanced JSON object if extra text exists
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]

        return text.strip()

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

        cleaned = self._clean_json_text(res.text)

        try:
            obj = json.loads(cleaned)
        except Exception as e:
            raise RuntimeError(f"INVALID_REQUEST: Perplexity returned non-JSON: {res.text[:200]}") from e

        if not isinstance(obj, dict):
            raise RuntimeError(f"INVALID_REQUEST: Perplexity JSON must be an object, got {type(obj).__name__}")

        obj.setdefault("verdict", "ERROR")
        obj.setdefault("confidence", 0.0)
        obj.setdefault("citations", [])
        obj.setdefault("summary", "")
        return obj
