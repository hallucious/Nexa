"""Legacy provider compatibility module.

Deprecated: retained only for legacy step-contract coverage; new provider work should use provider_adapter_contract.py and platform/provider_executor.py.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional

from src.providers.legacy_provider_trace import ProviderTrace


@dataclass
class ProviderResult:
    text: str
    raw_response: Any
    provider_name: str
    latency_ms: Optional[float] = None
    trace: Optional[ProviderTrace] = None
