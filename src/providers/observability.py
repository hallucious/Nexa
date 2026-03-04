
from __future__ import annotations
import time


class ProviderMetrics:
    def __init__(self):
        self.latency_ms: float | None = None
        self.cost: float | None = None
        self.error_rate: float | None = None


def record_latency(start_time: float) -> float:
    return (time.time() - start_time) * 1000


def attach_metrics(provider, latency_ms: float):
    metrics = getattr(provider, "metrics", None)
    if metrics is None:
        metrics = ProviderMetrics()
        provider.metrics = metrics

    metrics.latency_ms = latency_ms
