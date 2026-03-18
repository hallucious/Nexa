
from __future__ import annotations
from typing import Iterable, Any, List


class ProviderHealthSnapshot:
    def __init__(self, healthy: bool = True):
        self.healthy = healthy


def apply_routing_policy(providers: Iterable[Any]) -> List[Any]:
    """Minimal RoutingPolicy MVP.

    Removes providers marked unhealthy.
    """
    result = []
    for p in providers:
        health = getattr(p, "health", None)
        if health and not getattr(health, "healthy", True):
            continue
        result.append(p)
    return result
