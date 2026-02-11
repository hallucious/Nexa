from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from src.utils.env import load_dotenv
from src.providers.safe_mode import apply_safe_mode_text, normalize_text


@dataclass
class OpenAITextResult:
    text: str
    raw: Dict[str, Any]


class OpenAIProvider:
    """
    Stdlib-only OpenAI client (Responses API).

    Env:
      OPENAI_API_KEY (required)
      OPENAI_MODEL   (optional, default: "gpt-4.1")

    Notes:
    - Uses HTTPS via urllib only (no external deps).
    - SAFE_MODE is honored by wrapping the prompt (apply_safe_mode_text).
    """

    API_URL = "https://api.openai.com/v1/responses"

    def __init__(self, api_key: str, *, model: str = "gpt-4.1") -> None:
        self.api_key = api_key.strip()
        self.model = (model or "gpt-4.1").strip()

    @staticmethod
    def from_env() -> Optional["OpenAIProvider"]:
        load_dotenv()  # does not override existing env vars
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return None
        model = os.getenv("OPENAI_MODEL", "gpt-4.1").strip()
        return OpenAIProvider(api_key=api_key, model=model)

    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 512,
        timeout_sec: int = 30,
    ) -> Tuple[str, Dict[str, Any], Optional[Exception]]:
        """
        Returns (text, raw_response, error).
        Caller is responsible for JSON parsing if needed.
        """
        prompt = apply_safe_mode_text(prompt)
        prompt = normalize_text(prompt)

        payload: Dict[str, Any] = {
            "model": self.model,
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                }
            ],
            "temperature": float(temperature),
            "max_output_tokens": int(max_output_tokens),
        }

        req = urllib.request.Request(
            url=self.API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                raw_bytes = resp.read()
                raw: Dict[str, Any] = json.loads(raw_bytes.decode("utf-8"))
        except Exception as e:
            return "", {"error": str(e)}, e

        # Extract output text defensively
        text = ""
        try:
            # responses API: output[].content[].text
            out = raw.get("output", [])
            if out and isinstance(out, list):
                content = out[0].get("content", [])
                if content and isinstance(content, list):
                    # find first text-like item
                    for item in content:
                        if isinstance(item, dict) and item.get("type") in ("output_text", "text"):
                            text = str(item.get("text", "")).strip()
                            break
        except Exception:
            text = ""

        return text, raw, None
