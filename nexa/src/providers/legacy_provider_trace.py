"""Legacy provider compatibility module.

Deprecated: retained only for legacy step-contract coverage; new provider work should use provider_adapter_contract.py and platform/provider_executor.py.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ProviderTrace:
    attempted_providers: List[str] = field(default_factory=list)
    selected_provider: Optional[str] = None
    failures: Dict[str, str] = field(default_factory=dict)
    latency_ms: Optional[float] = None
    routing_policy: Optional[str] = None

    def record_attempt(self, provider: str) -> None:
        self.attempted_providers.append(provider)

    def record_failure(self, provider: str, reason: str) -> None:
        self.failures[provider] = reason

    def record_selected(self, provider: str) -> None:
        self.selected_provider = provider

    def record_latency(self, latency_ms: float) -> None:
        self.latency_ms = latency_ms
