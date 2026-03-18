
from __future__ import annotations

class MockProvider:
    def __init__(self, name, healthy=True):
        self.name = name
        self.healthy = healthy

    def fingerprint(self):
        return f"fp-{self.name}"

    def call(self, request):
        if not self.healthy:
            e = Exception("provider down")
            setattr(e, "retryable", True)
            raise e
        return {"ok": True, "provider": self.name}


def routing_policy_filter(providers):
    """Very small MVP policy:
    - unhealthy provider는 건너뜀
    """
    return [p for p in providers if getattr(p, "healthy", True)]


def test_step98_routing_policy_skips_unhealthy():
    p1 = MockProvider("A", healthy=False)
    p2 = MockProvider("B", healthy=True)

    filtered = routing_policy_filter([p1, p2])

    assert len(filtered) == 1
    assert filtered[0].name == "B"
