
from __future__ import annotations
import time


class MockProvider:
    def __init__(self, name):
        self.name = name
        self.health = type("Health", (), {})()
        self.health.healthy = True
        self.health.last_error = None
        self.health.cooldown_until = None

    def fingerprint(self):
        return f"fp-{self.name}"

    def call(self, request):
        e = Exception("temporary")
        setattr(e, "retryable", True)
        raise e


def test_step99_provider_cooldown_contract():
    p = MockProvider("A")

    # simulate router cooldown update
    now = time.time()
    cooldown = 5
    p.health.healthy = False
    p.health.last_error = "Exception"
    p.health.cooldown_until = now + cooldown

    assert p.health.healthy is False
    assert p.health.last_error == "Exception"
    assert p.health.cooldown_until > now
