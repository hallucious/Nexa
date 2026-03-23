from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.providers.provider_contract import ProviderResult, compute_provider_fingerprint
from src.providers.universal_provider import UniversalProvider
from src.providers.adapters.base_adapter import AdapterConfig
from src.providers.adapters.openai_compatible_adapter import OpenAICompatibleAdapter


@dataclass(frozen=True)
class GPTTextResult:
    text: str
    raw: Dict[str, Any]


class GPTProvider:
    """OpenAI GPT provider implemented via UniversalProvider + OpenAICompatibleAdapter.

    Keeps legacy constructor/env surface for stability.
    """

    API_URL: str = "https://api.openai.com/v1/responses"

    def __init__(self, api_key: str, *, model: str = "gpt-5.2", timeout_sec: int = 60) -> None:
        self.api_key = (api_key or "").strip()
        self.model = (model or "gpt-5.2").strip()
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
    def from_env(cls) -> "GPTProvider":
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
        model = (os.getenv("GPT_MODEL", "") or "gpt-5.2").strip()
        timeout = (os.getenv("OPENAI_TIMEOUT_SEC", "") or "").strip()
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
        # Delegate to UniversalProvider (SAFE_MODE handled there).
        return self._universal.generate_text(
            prompt=prompt,
            temperature=float(temperature),
            max_output_tokens=int(max_output_tokens),
            instructions=instructions,
        )
