from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AutoRecoveryProviderRuntimeMetrics:
    provider_key: str
    latency_ms: Optional[float] = None
    success_rate: Optional[float] = None

    def __post_init__(self) -> None:
        if not str(self.provider_key).strip():
            raise ValueError("AutoRecoveryProviderRuntimeMetrics.provider_key must be non-empty")
        if self.latency_ms is not None and float(self.latency_ms) <= 0:
            raise ValueError("AutoRecoveryProviderRuntimeMetrics.latency_ms must be > 0 when provided")
        if self.success_rate is not None:
            value = float(self.success_rate)
            if value < 0 or value > 1:
                raise ValueError("AutoRecoveryProviderRuntimeMetrics.success_rate must be between 0 and 1")
