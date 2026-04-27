from __future__ import annotations

import time
from typing import Dict, Optional, Tuple

from .pricing_models import ProviderCost


class PricingCache:
    def __init__(self, ttl_seconds: int = 300) -> None:
        self._ttl = ttl_seconds
        self._store: Dict[str, Tuple[float, ProviderCost]] = {}

    @staticmethod
    def cache_key(provider: str, model_ref: str | None = None) -> str:
        normalized_provider = str(provider or "").strip().lower()
        normalized_model = str(model_ref or "").strip().lower()
        return f"{normalized_provider}:{normalized_model}" if normalized_model else normalized_provider

    def get(self, provider: str, model_ref: str | None = None) -> Optional[ProviderCost]:
        key = self.cache_key(provider, model_ref)
        entry = self._store.get(key)
        if not entry and model_ref:
            entry = self._store.get(self.cache_key(provider))
        if not entry:
            return None

        ts, value = entry
        if time.time() - ts > self._ttl:
            self._store.pop(key, None)
            if model_ref:
                self._store.pop(self.cache_key(provider), None)
            return None

        return value

    def set(self, provider: str, cost: ProviderCost, model_ref: str | None = None) -> None:
        key = self.cache_key(provider, model_ref or cost.model_ref)
        self._store[key] = (time.time(), cost)
