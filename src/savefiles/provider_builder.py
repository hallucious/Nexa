"""
savefile_provider_builder.py

Builds a ProviderRegistry from savefile resources.

Encoding fix:
    urllib.request sends HTTP headers via http.client which encodes them using
    latin-1. Any non-ASCII character in the Authorization header (api_key) or
    extra_headers causes a UnicodeEncodeError that surfaces as:
        SAFE_MODE failed: 'latin-1' codec can't encode characters

    Fix: sanitize api_key to pure ASCII before passing to provider constructors.
"""

from __future__ import annotations

import os

from src.platform.provider_executor import GenerateTextProviderBridge
from src.platform.provider_registry import ProviderRegistry
from typing import TYPE_CHECKING

from src.contracts.savefile_format import Savefile

if TYPE_CHECKING:
    from src.storage.execution_savefile_adapter import ExecutionSavefileAdapter
from src.contracts.provider_contract import (
    ProviderRequest,
    ProviderResult as ContractProviderResult,
)


def _to_ascii_safe(s: str) -> str:
    """Strip all non-ASCII characters — prevents latin-1 HTTP header failures."""
    if isinstance(s, bytes):
        return s.decode("utf-8", errors="ignore")
    return s.encode("ascii", errors="ignore").decode("ascii")


def build_provider_registry_from_savefile(savefile: Savefile | "ExecutionSavefileAdapter") -> ProviderRegistry:
    registry = ProviderRegistry()

    for provider_id, provider_resource in savefile.resources.providers.items():
        provider_type = provider_resource.type
        cfg = provider_resource.config or {}
        model = provider_resource.model

        if provider_type in ("openai", "gpt"):
            from src.providers.gpt_provider import GPTProvider

            api_key = _to_ascii_safe(os.getenv("OPENAI_API_KEY", "").strip())
            timeout_sec = int(cfg.get("timeout_sec", 60))
            provider_instance = GenerateTextProviderBridge(
                GPTProvider(
                    api_key=api_key,
                    model=model or "gpt-4o-mini",
                    timeout_sec=timeout_sec,
                ),
                provider_name="gpt",
            )

        elif provider_type in ("anthropic", "claude"):
            from src.providers.claude_provider import ClaudeProvider

            api_key = _to_ascii_safe(os.getenv("ANTHROPIC_API_KEY", "").strip())
            timeout_sec = int(cfg.get("timeout_sec", 60))
            provider_instance = GenerateTextProviderBridge(
                ClaudeProvider(
                    api_key=api_key,
                    model=model or ClaudeProvider.DEFAULT_MODEL,
                    timeout_sec=timeout_sec,
                ),
                provider_name="anthropic",
            )

        elif provider_type == "test":
            provider_instance = _create_test_provider()

        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

        registry.register(provider_id, provider_instance)

    return registry


def _create_test_provider():
    class TestProvider:
        def execute(self, request: ProviderRequest) -> ContractProviderResult:
            text = f"[TEST] {request.prompt}"
            return ContractProviderResult(
                output={"text": text},
                raw_text=text,
                structured=None,
                artifacts=[],
                trace={"provider": "test"},
                error=None,
            )

    return TestProvider()
