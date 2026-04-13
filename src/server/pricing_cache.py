import time
from typing import Dict, Optional, Tuple

from .pricing_models import ProviderCost


class PricingCache:
    def __init__(self, ttl_seconds: int = 300) -> None:
        self._ttl = ttl_seconds
        self._store: Dict[str, Tuple[float, ProviderCost]] = {}

    def get(self, provider: str) -> Optional[ProviderCost]:
        entry = self._store.get(provider)
        if not entry:
            return None

        ts, value = entry
        if time.time() - ts > self._ttl:
            self._store.pop(provider, None)
            return None

        return value

    def set(self, provider: str, cost: ProviderCost) -> None:
        self._store[provider] = (time.time(), cost)
