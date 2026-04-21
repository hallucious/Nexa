from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional, Tuple

from src.providers.provider_adapter_contract import ProviderRequest

from .base_adapter import AdapterConfig, ProviderAdapter, StreamChunk


@dataclass
class OpenAICompatibleAdapter(ProviderAdapter):
    """Adapter for OpenAI-compatible REST APIs.

    Supports two shapes:
    - mode='responses' -> POST /v1/responses (OpenAI Responses API style)
    - mode='chat_completions' -> POST /chat/completions (OpenAI-compatible legacy)
    """

    config: AdapterConfig
    mode: str = "responses"  # 'responses' | 'chat_completions'

    @property
    def name(self) -> str:  # type: ignore[override]
        return f"openai_compatible:{self.mode}"

    def build_payload(self, req: ProviderRequest) -> Dict[str, Any]:  # type: ignore[override]
        if self.mode == "responses":
            payload: Dict[str, Any] = {
                "model": (req.model or self.config.model).strip(),
                "input": req.prompt,
                "temperature": float(req.temperature),
                "max_output_tokens": int(req.max_output_tokens),
            }
            if req.stop:
                payload["stop"] = req.stop
            if req.seed is not None:
                payload["seed"] = int(req.seed)
            return payload

        # chat completions
        payload = {
            "model": (req.model or self.config.model).strip(),
            "messages": [{"role": "user", "content": req.prompt}],
            "temperature": float(req.temperature),
            "max_tokens": int(req.max_output_tokens),
        }
        if req.stop:
            payload["stop"] = req.stop
        if req.seed is not None:
            # Not universally supported, but safe to include for compatible backends.
            payload["seed"] = int(req.seed)
        return payload

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[override]
        data = json.dumps(payload).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        if self.config.extra_headers:
            headers.update({
                k.encode("ascii", errors="ignore").decode("ascii"):
                str(v).encode("ascii", errors="ignore").decode("ascii")
                for k, v in self.config.extra_headers.items()
            })

        req = urllib.request.Request(
            self.config.endpoint,
            data=data,
            method="POST",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=self.config.timeout_sec) as resp:
            raw_bytes = resp.read()
        raw_text = raw_bytes.decode("utf-8", errors="replace")
        raw: Dict[str, Any] = json.loads(raw_text)
        return raw

    def stream(self, payload: Dict[str, Any]) -> Iterator[StreamChunk]:  # type: ignore[override]
        """Foundation streaming path with safe non-stream fallback."""
        raw = self.send(dict(payload))
        text, tokens_used = self.parse(raw)
        yield {
            "text": text,
            "raw": raw,
            "tokens_used": tokens_used,
            "is_final": True,
            "native_stream": False,
        }

    def parse(self, raw: Dict[str, Any]) -> Tuple[str, Optional[int]]:  # type: ignore[override]
        if self.mode == "responses":
            # Extract text from Responses API format:
            # output[*].content[*].type == "output_text"
            parts = []
            for item in (raw.get("output") or []):
                for c in (item.get("content") or []):
                    if c.get("type") == "output_text" and isinstance(c.get("text"), str):
                        parts.append(c["text"])
            text = "\n".join([p for p in parts if p.strip()]).strip()
            if not text and isinstance(raw.get("output_text"), str):
                text = raw["output_text"].strip()
            tokens_used = None
            try:
                tokens_used = (raw.get("usage") or {}).get("output_tokens")
            except Exception:
                tokens_used = None
            return text, tokens_used

        # chat completions
        text = ""
        try:
            choices = raw.get("choices") or []
            if choices:
                msg = (choices[0] or {}).get("message") or {}
                if isinstance(msg.get("content"), str):
                    text = msg["content"]
        except Exception:
            text = ""
        tokens_used = None
        try:
            usage = raw.get("usage") or {}
            tokens_used = usage.get("completion_tokens") or usage.get("total_tokens")
        except Exception:
            tokens_used = None
        return (text or "").strip(), tokens_used

    def fingerprint_components(self) -> Dict[str, Any]:  # type: ignore[override]
        return {
            "adapter": self.name,
            "endpoint": self.config.endpoint,
            "model": self.config.model,
            "timeout_sec": self.config.timeout_sec,
        }
