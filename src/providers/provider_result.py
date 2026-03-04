
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional

from src.providers.provider_trace import ProviderTrace


@dataclass
class ProviderResult:
    text: str
    raw_response: Any
    provider_name: str
    latency_ms: Optional[float] = None
    trace: Optional[ProviderTrace] = None
