"""Legacy provider compatibility module.

Deprecated: retained only for legacy step-contract coverage; new provider work should use provider_adapter_contract.py and platform/provider_executor.py.
"""

from __future__ import annotations
from typing import Any, Optional

from src.providers.universal_provider import UniversalProvider
from src.providers.legacy_provider_result import ProviderResult
from src.providers.legacy_provider_trace import ProviderTrace


class ProviderExecution:
    """Bridge between Circuit nodes and UniversalProvider."""

    def __init__(self, provider: UniversalProvider):
        self.provider = provider

    def execute(
        self,
        *,
        prompt: str,
        model: str,
        trace: Optional[ProviderTrace] = None,
        **kwargs: Any,
    ) -> ProviderResult:

        if trace is None:
            trace = ProviderTrace()

        result = self.provider.generate(
            prompt=prompt,
            model=model,
            trace=trace,
            **kwargs,
        )

        if not isinstance(result, ProviderResult):
            raise TypeError("Provider must return ProviderResult")

        return result
