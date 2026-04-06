from __future__ import annotations

import os

from src.providers.env_diagnostics import resolve_api_key_or_raise
from typing import Optional

from src.providers.provider_contract import ProviderResult, compute_provider_fingerprint
from src.providers.universal_provider import UniversalProvider
from src.providers.adapters.base_adapter import AdapterConfig
from src.providers.adapters.anthropic_messages_adapter import AnthropicMessagesAdapter


class ClaudeProvider:
    """Stdlib-only Anthropic Claude client via UniversalProvider (AI-PROVIDER v1.1.x)."""

    API_URL = "https://api.anthropic.com/v1/messages"
    ANTHROPIC_VERSION = "2023-06-01"
    DEFAULT_MODEL = "claude-sonnet-4-6"

    def __init__(self, api_key: str, *, model: str = DEFAULT_MODEL, timeout_sec: int = 60) -> None:
        self.api_key = (api_key or "").strip()
        self.model = (model or self.DEFAULT_MODEL).strip()
        self.timeout_sec = int(timeout_sec)

        cfg = AdapterConfig(
            api_key=self.api_key,
            model=self.model,
            endpoint=self.API_URL,
            timeout_sec=self.timeout_sec,
        )
        adapter = AnthropicMessagesAdapter(config=cfg, anthropic_version=self.ANTHROPIC_VERSION)
        self._universal = UniversalProvider(adapter=adapter, safe_mode_enabled=True)

    @classmethod
    def from_env(cls) -> "ClaudeProvider":
        api_key = resolve_api_key_or_raise("ANTHROPIC_API_KEY")
        model = (os.environ.get("ANTHROPIC_MODEL") or cls.DEFAULT_MODEL).strip()
        timeout = (os.environ.get("ANTHROPIC_TIMEOUT_SEC") or "").strip()
        timeout_i = int(timeout) if timeout.isdigit() else 60
        return cls(api_key, model=model, timeout_sec=timeout_i)

    def fingerprint(self) -> str:
        info = {
            "provider": type(self).__name__,
            "api": "anthropic.messages",
            "endpoint": self.API_URL,
            "anthropic_version": self.ANTHROPIC_VERSION,
            "model": self.model,
            "timeout_sec": self.timeout_sec,
            "safe_mode": True,
        }
        return compute_provider_fingerprint(info)

    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
        instructions: Optional[str] = None,
    ) -> ProviderResult:
        return self._universal.generate_text(
            prompt=prompt,
            temperature=float(temperature),
            max_output_tokens=int(max_output_tokens),
            instructions=instructions,
        )
