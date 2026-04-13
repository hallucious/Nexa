from typing import Dict, Optional

from .pricing_cache import PricingCache
from .pricing_models import ProviderCost


class PricingResolver:
    def __init__(
        self,
        external_table: Dict[str, float],
        cache: PricingCache,
        workspace_override: Optional[Dict[str, float]] = None,
    ) -> None:
        self.external_table = external_table
        self.cache = cache
        self.workspace_override = workspace_override or {}

    def resolve(self, provider: str) -> Optional[ProviderCost]:
        if provider in self.external_table:
            cost = ProviderCost(
                provider=provider,
                cost_ratio=self.external_table[provider],
                source="external",
            )
            self.cache.set(provider, cost)
            return cost

        cached = self.cache.get(provider)
        if cached is not None:
            return ProviderCost(
                provider=provider,
                cost_ratio=cached.cost_ratio,
                source="cache",
            )

        if provider in self.workspace_override:
            return ProviderCost(
                provider=provider,
                cost_ratio=self.workspace_override[provider],
                source="workspace",
            )

        return None
