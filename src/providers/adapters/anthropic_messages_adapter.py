from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from src.providers.provider_contract import ProviderRequest

from .base_adapter import AdapterConfig, ProviderAdapter


@dataclass
class AnthropicMessagesAdapter(ProviderAdapter):
    config: AdapterConfig
    anthropic_version: str = "2023-06-01"

    @property
    def name(self) -> str:  # type: ignore[override]
        return "anthropic_messages"

    def build_payload(self, req: ProviderRequest) -> Dict[str, Any]:  # type: ignore[override]
        return {
            "model": (req.model or self.config.model).strip(),
            "max_tokens": int(req.max_output_tokens),
            "messages": [{"role": "user", "content": req.prompt}],
            "temperature": float(req.temperature),
        }

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[override]
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.config.endpoint,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.config.api_key,
                "anthropic-version": self.anthropic_version,
            },
        )
        with urllib.request.urlopen(req, timeout=self.config.timeout_sec) as resp:
            raw_bytes = resp.read()
        raw_text = raw_bytes.decode("utf-8", errors="replace")
        return json.loads(raw_text)

    def parse(self, raw: Dict[str, Any]) -> Tuple[str, Optional[int]]:  # type: ignore[override]
        parts = []
        for item in (raw.get("content") or []):
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        text = "\n".join([p for p in parts if p.strip()]).strip()
        tokens_used = None
        try:
            tokens_used = (raw.get("usage") or {}).get("output_tokens")
        except Exception:
            tokens_used = None
        return text, tokens_used

    def fingerprint_components(self) -> Dict[str, Any]:  # type: ignore[override]
        return {
            "adapter": self.name,
            "endpoint": self.config.endpoint,
            "model": self.config.model,
            "anthropic_version": self.anthropic_version,
            "timeout_sec": self.config.timeout_sec,
        }
