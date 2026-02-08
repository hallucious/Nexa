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

    - Uses env:
        GEMINI_API_KEY
        GEMINI_MODEL (optional, default: "gemini-1.5-pro")
    - Network call is made ONLY when GEMINI_API_KEY exists.
    - Returns a structured verdict JSON to keep Gate2 deterministic when disabled.
    """

    def __init__(self, api_key: str, *, model: str = "gemini-1.5-pro") -> None:
        self.api_key = api_key.strip()
        self.model = (model or "gemini-1.5-pro").strip()

    @staticmethod
    def from_env() -> Optional["GeminiProvider"]:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            return None
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-pro").strip()
        return GeminiProvider(api_key, model=model)

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

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )

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

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception as e:
            return GeminiResult(
                verdict="UNKNOWN",
                rationale=f"Gemini call failed: {type(e).__name__}: {e}",
                raw={"error": str(e)},
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
            return GeminiResult(verdict=verdict, rationale=rationale, raw={"api": raw, "model_text": text})
        except Exception as e:
            return GeminiResult(
                verdict="UNKNOWN",
                rationale=f"Model output not valid JSON: {type(e).__name__}: {e}",
                raw={"api": raw, "model_text": text},
            )
