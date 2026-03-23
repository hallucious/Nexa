from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class CodexTextResult:
    text: str
    raw: Dict[str, Any]

from src.providers.provider_contract import ProviderResult, compute_provider_fingerprint
from src.providers.universal_provider import UniversalProvider
from src.providers.adapters.base_adapter import AdapterConfig
from src.providers.adapters.openai_compatible_adapter import OpenAICompatibleAdapter


class CodexProvider:
    """OpenAI Codex-style provider (Responses API) via UniversalProvider."""

    API_URL = "https://api.openai.com/v1/responses"
    DEFAULT_MODEL = "gpt-5.2-codex"

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
        adapter = OpenAICompatibleAdapter(config=cfg, mode="responses")
        self._universal = UniversalProvider(adapter=adapter, safe_mode_enabled=True)

    @classmethod
    def from_env(cls) -> "CodexProvider":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
            "[ERROR] OPENAI_API_KEY not found\n\n"
            "Fix:\n"
            "1. Create a .env file in project root\n"
            "2. Add:\n"
            "   OPENAI_API_KEY=your_key_here\n\n"
            "OR\n\n"
            "export OPENAI_API_KEY=your_key_here\n"
        )
        model = (os.getenv("CODEX_MODEL", "") or cls.DEFAULT_MODEL).strip()
        timeout = (os.getenv("CODEX_TIMEOUT_SEC", "") or "").strip()
        timeout_i = int(timeout) if timeout.isdigit() else 60
        return cls(api_key, model=model, timeout_sec=timeout_i)

    def fingerprint(self) -> str:
        info = {
            "provider": type(self).__name__,
            "api": "openai.responses",
            "endpoint": self.API_URL,
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
