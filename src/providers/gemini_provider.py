from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class GeminiResult:
    verdict: str  # "SAME" | "DRIFT" | "VIOLATION" | "UNKNOWN"
    rationale: str
    raw: Dict[str, Any]


class GeminiProvider:
    """
    Stdlib-only Gemini client.

    Policy:
    - Network call is made ONLY when:
        (1) GEMINI_API_KEY exists, AND
        (2) caller explicitly enables the feature (Gate-level switch)

    Env:
      GEMINI_API_KEY
      GEMINI_MODEL (default: "gemini-1.5-pro")
      GEMINI_API_URL (optional override; if omitted use official endpoint)
      GEMINI_TIMEOUT_SEC (default: 30)
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gemini-1.5-pro",
        api_url: Optional[str] = None,
        timeout_sec: int = 30,
    ) -> None:
        self.api_key = api_key.strip()
        self.model = (model or "gemini-1.5-pro").strip()
        self.api_url_override = (api_url or "").strip() or None
        self.timeout_sec = int(timeout_sec) if int(timeout_sec) > 0 else 30

    @staticmethod
    def from_env() -> Optional["GeminiProvider"]:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            return None
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-pro").strip()
        api_url = os.getenv("GEMINI_API_URL", "").strip() or None
        timeout_sec = int(os.getenv("GEMINI_TIMEOUT_SEC", "30").strip() or "30")
        return GeminiProvider(api_key, model=model, api_url=api_url, timeout_sec=timeout_sec)

    def _build_url(self) -> str:
        if self.api_url_override:
            # If user provided a full URL (including key or not), we respect it as-is.
            # If they provided base url, they must include key handling themselves.
            return self.api_url_override
        return (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )

    def judge_continuity(self, *, pic_text: str, current_text: str) -> GeminiResult:
        """
        Ask Gemini to classify semantic continuity:
          SAME | DRIFT | VIOLATION

        Must respond in strict JSON:
        {
          "verdict": "SAME|DRIFT|VIOLATION",
          "rationale": "..."
        }
        """
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

        url = self._build_url()

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 512,
            },
        }

        req = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        request_meta = {
            "provider": "gemini",
            "model": self.model,
            "api_url_override": bool(self.api_url_override),
            "timeout_sec": self.timeout_sec,
            "generationConfig": payload.get("generationConfig", {}),
        }

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                raw = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception as e:
            return GeminiResult(
                verdict="UNKNOWN",
                rationale=f"Gemini call failed: {type(e).__name__}: {e}",
                raw={"error": str(e), "request": request_meta},
            )

        # Extract model text
        text = ""
        try:
            candidates = raw.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts and isinstance(parts[0], dict):
                    text = str(parts[0].get("text", "")).strip()
        except Exception:
            text = ""

        # Parse strict JSON from model output
        try:
            parsed = json.loads(text)
            verdict = str(parsed.get("verdict", "")).strip().upper()
            rationale = str(parsed.get("rationale", "")).strip()
            if verdict not in ("SAME", "DRIFT", "VIOLATION"):
                verdict = "UNKNOWN"
            return GeminiResult(
                verdict=verdict,
                rationale=rationale,
                raw={"api": raw, "model_text": text, "request": request_meta},
            )
        except Exception as e:
            return GeminiResult(
                verdict="UNKNOWN",
                rationale=f"Model output not valid JSON: {type(e).__name__}: {e}",
                raw={"api": raw, "model_text": text, "request": request_meta},
            )
