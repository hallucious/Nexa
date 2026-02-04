from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, List


class PerplexityProvider:
    """
    Minimal Perplexity API client.
    Purpose: evidence retrieval, not decision making.
    """

    API_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Perplexity API key is required")
        self.api_key = api_key

    def verify(self, statement: str) -> Dict[str, Any]:
        """
        Returns:
        {
          "verdict": "OK" | "WARN" | "ERROR",
          "confidence": float,
          "citations": [ { "title": str, "url": str } ],
          "summary": str
        }
        """
        payload = {
            "model": "sonar-pro",
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

        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        content = data["choices"][0]["message"]["content"]

        # Extremely conservative parsing (text → structured hint)
        verdict = "WARN"
        if "ERROR" in content.upper():
            verdict = "ERROR"
        elif "OK" in content.upper():
            verdict = "OK"

        return {
            "verdict": verdict,
            "confidence": 0.5,
            "citations": data.get("citations", []),
            "summary": content.strip(),
        }
