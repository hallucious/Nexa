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
    Semantic continuity judgement.

    - Lossless preprocessing for TOO_LONG:
      Split CURRENT into deterministic chunks and evaluate each chunk against PIC.
      Aggregate the worst verdict (VIOLATION > DRIFT > SAME).
    """

    def _build_prompt(cur: str) -> str:
        base = (
            "You are a strict reviewer for project semantic continuity.\n"
            "Given a Project Identity Contract (PIC) and the current design text, "
            "decide whether the current work is still the same project.\n\n"
            "Return ONLY valid JSON with keys: verdict, rationale.\n"
            "verdict must be one of: SAME, DRIFT, VIOLATION.\n\n"
            "=== PIC ===\n"
            f"{pic_text}\n\n"
            "=== CURRENT ===\n"
            f"{cur}\n"
        )
        return apply_safe_mode_text(base)

    reason = safe_mode_reason().upper()

    if reason == "TOO_LONG" or len(current_text) > 24000:
        chunks = split_into_chunks(current_text, max_chars=8000)
        order = {"SAME": 0, "DRIFT": 1, "VIOLATION": 2, "UNKNOWN": 3}
        worst = "SAME"
        rationales = []
        raw_chunks = []

        for i, chunk in enumerate(chunks, start=1):
            prompt = _build_prompt(chunk)
            text, raw, err = self.generate_text(prompt=prompt, temperature=0.0, max_output_tokens=512)
            raw_chunks.append({"chunk_index": i, "chunk_len": len(chunk), "raw": raw, "error": str(err) if err else None})

            if err is not None:
                worst = "UNKNOWN"
                rationales.append(f"[chunk {i}/{len(chunks)}] call failed: {type(err).__name__}: {err}")
                continue

            try:
                parsed = json.loads(text)
                verdict = str(parsed.get("verdict", "")).strip().upper()
                rationale = str(parsed.get("rationale", "")).strip()
            except Exception:
                verdict = "UNKNOWN"
                rationale = "Model did not return valid JSON"

            if verdict not in ("SAME", "DRIFT", "VIOLATION"):
                verdict = "UNKNOWN"

            rationales.append(f"[chunk {i}/{len(chunks)}] {verdict}: {rationale}")
            if order.get(verdict, 3) > order.get(worst, 0):
                worst = verdict

            if worst == "VIOLATION":
                break

        return GeminiResult(verdict=worst, rationale="\n".join(rationales).strip(), raw={"mode": "chunked", "chunks": raw_chunks})

    # Normal path (single call)
    prompt = _build_prompt(current_text)
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
    except Exception:
        return GeminiResult(
            verdict="UNKNOWN",
            rationale=f"Model did not return valid JSON: {text[:200]}",
            raw={"text": text, "raw": raw},
        )

    return GeminiResult(verdict=verdict, rationale=rationale, raw=raw)


def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 512,
        timeout_sec: int = 30,
    ) -> tuple[str, Dict[str, Any], Optional[Exception]]:
        """Generic text generation helper.

        Returns (text, raw_response, error).

        Notes:
        - Stdlib-only.
        - Caller is responsible for JSON parsing if needed.
        """

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )

        prompt = apply_safe_mode_text(prompt)

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": float(temperature),
                "maxOutputTokens": int(max_output_tokens),
            },
        }

        req = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=int(timeout_sec)) as resp:
                raw = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception as e:
            return ("", {"error": str(e)}, e)

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

        return (text, raw, None)
