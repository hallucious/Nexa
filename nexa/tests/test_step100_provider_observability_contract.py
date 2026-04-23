from __future__ import annotations

import time

from src.providers.provider_metrics import ProviderRuntimeMetrics, attach_metrics, record_latency


class MockProvider:
    pass


def test_step100_latency_recording():
    start = time.time()
    time.sleep(0.01)
    latency = record_latency(start)

    assert latency > 0


def test_step100_attach_metrics():
    p = MockProvider()

    attach_metrics(p, 123.4)

    assert hasattr(p, "metrics")
    assert isinstance(p.metrics, ProviderRuntimeMetrics)
    assert p.metrics.latency_ms == 123.4
