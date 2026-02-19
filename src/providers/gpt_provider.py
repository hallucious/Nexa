from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from src.providers.safe_mode import apply_safe_mode_prefix, run_safe_mode


@dataclass(frozen=True)
class GPTTextResult:
    text: str
    raw: Dict[str, Any]
    err: Optional[BaseException] = None


class GPTProvider:
    """
    Minimal OpenAI Responses API client (stdlib-only) with SAFE_MODE v2.

    - Provides generate_text(prompt=..., temperature=..., max_output_tokens=...) -> (text, raw, err)
    - Default model: env GPT_MODEL, fallback to "gpt-5.2"
    - Requires env OPENAI_API_KEY
    """
    API_URL = "https://api.openai.com/v1/responses"

    def __init__(self, api_key: str, *, model: str = "gpt-5.2", timeout_sec: int = 60) -> None:
        self.api_key = api_key
        self.model = (model or "gpt-5.2").strip()
        self.timeout_sec = int(timeout_sec)

    @classmethod
    def from_env(cls) -> "GPTProvider":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing")
        model = (os.getenv("GPT_MODEL", "") or "gpt-5.2").strip()
        timeout = (os.getenv("OPENAI_TIMEOUT_SEC", "") or "").strip()
        timeout_i = int(timeout) if timeout.isdigit() else 60
        return cls(api_key, model=model, timeout_sec=timeout_i)

    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
        instructions: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any], Optional[BaseException]]:
        # SAFE_MODE can sanitize/transform the prompt to reduce provider refusals.
        safe_prompt = apply_safe_mode_prefix(prompt or "")

        payload: Dict[str, Any] = {
            "model": self.model,
            "input": safe_prompt,
            "temperature": float(temperature),
            "max_output_tokens": int(max_output_tokens),
        }
        if instructions:
            payload["instructions"] = instructions

        def _http_call() -> Tuple[str, Dict[str, Any]]:
            import json
            import urllib.request

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.API_URL,
                data=data,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                raw_bytes = resp.read()
                raw_text = raw_bytes.decode("utf-8", errors="replace")
                raw: Dict[str, Any] = json.loads(raw_text)

            # Extract text from Responses API format:
            # Look for output[*].content[*].type == "output_text" and join their "text" fields.
            text_parts = []
            for item in (raw.get("output") or []):
                for c in (item.get("content") or []):
                    if c.get("type") == "output_text" and isinstance(c.get("text"), str):
                        text_parts.append(c["text"])
            text = "\n".join([t for t in text_parts if t.strip()]).strip()

            # Fallback: SDK convenience 'output_text' isn't guaranteed in raw REST response,
            # but some responses may include it; use if present.
            if not text and isinstance(raw.get("output_text"), str):
                text = raw["output_text"].strip()

            return text, raw

        try:
            text, raw = run_safe_mode(_http_call)
            return text, raw, None
        except Exception as e:
            return "", {}, e
