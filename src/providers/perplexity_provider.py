from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, Optional


class PerplexityProvider:
    """
    Minimal Perplexity API client (stdlib-only).

    Purpose: evidence retrieval, not decision making.

    Env (recommended):
      PERPLEXITY_API_KEY
      PERPLEXITY_MODEL (default: "sonar-pro")
      PERPLEXITY_TIMEOUT_SEC (default: 20)
    """

    API_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(self, api_key: str, *, model: str = "sonar-pro", timeout_sec: int = 20):
        if not api_key:
            raise ValueError("Perplexity API key is required")
        self.api_key = api_key.strip()
        self.model = (model or "sonar-pro").strip()
        self.timeout_sec = int(timeout_sec) if int(timeout_sec) > 0 else 20

    @staticmethod
    def from_env() -> Optional["PerplexityProvider"]:
        api_key = os.getenv("PERPLEXITY_API_KEY", "").strip()
        if not api_key:
            return None
        model = os.getenv("PERPLEXITY_MODEL", "sonar-pro").strip()
        timeout_sec = int(os.getenv("PERPLEXITY_TIMEOUT_SEC", "20").strip() or "20")
        try:
            return PerplexityProvider(api_key, model=model, timeout_sec=timeout_sec)
        except Exception:
            return None

    def verify(self, statement: str) -> Dict[str, Any]:
        """
        Returns:
        {
          "verdict": "OK" | "WARN" | "ERROR",
          "confidence": float,
          "citations": [ { "title": str, "url": str } ],
          "summary": str,
          "raw": dict,            # raw api response (best-effort)
          "request": dict         # request metadata (no secrets)
        }

        Notes:
        - This is intentionally conservative. It does NOT try to perfectly parse; it preserves raw text.
        - On network/parse failure, caller should fall back to deterministic rule-based audit.
        """
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a fact-checking assistant. "
                        "Classify the statement as OK, WARN, or ERROR. "
                        "Provide a short justification and cite sources."
                    ),
                },
                {"role": "user", "content": statement},
            ],
        }

        req = urllib.request.Request(
            self.API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        request_meta = {
            "provider": "perplexity",
            "model": self.model,
            "timeout_sec": self.timeout_sec,
            "api_url": self.API_URL,
        }

        with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

        content = ""
        try:
            content = data["choices"][0]["message"]["content"]
        except Exception:
            content = json.dumps(data, ensure_ascii=False)

        # Extremely conservative parsing (text → structured hint)
        verdict = "WARN"
        up = content.upper()
        if "ERROR" in up:
            verdict = "ERROR"
        elif "OK" in up:
            verdict = "OK"

        return {
            "verdict": verdict,
            "confidence": 0.5,
            "citations": data.get("citations", []),
            "summary": str(content).strip(),
            "raw": data,
            "request": request_meta,
        }
