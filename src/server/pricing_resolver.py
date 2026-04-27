from __future__ import annotations

from typing import Dict, Mapping, Optional, Sequence

from .pricing_cache import PricingCache
from .pricing_models import ProviderCost
from src.server.provider_catalog_runtime import normalize_model_ref, normalize_provider_key, resolve_provider_model_cost


class PricingResolver:
    def __init__(
        self,
        external_table: Dict[str, float],
        cache: PricingCache,
        workspace_override: Optional[Dict[str, float]] = None,
        *,
        canonical_catalog_rows: Sequence[Mapping[str, object]] | None = None,
    ) -> None:
        self.external_table = self._normalize_pricing_table(external_table)
        self.cache = cache
        self.workspace_override = self._normalize_pricing_table(workspace_override or {})
        self.canonical_catalog_rows = canonical_catalog_rows

    @staticmethod
    def _normalize_pricing_table(table: Mapping[str, float]) -> Dict[str, float]:
        normalized: Dict[str, float] = {}
        for raw_key, raw_value in table.items():
            key = str(raw_key or "").strip().lower()
            if not key:
                continue
            if ":" in key:
                raw_provider, raw_model = key.split(":", 1)
                key = f"{normalize_provider_key(raw_provider)}:{normalize_model_ref(raw_model)}"
            else:
                key = normalize_provider_key(key)
            normalized[key] = float(raw_value)
        return normalized

    @staticmethod
    def _lookup_keys(provider: str, model_ref: str | None = None) -> tuple[str, ...]:
        provider_key = normalize_provider_key(provider)
        if model_ref and str(model_ref).strip():
            model_key = normalize_model_ref(model_ref)
            return (f"{provider_key}:{model_key}", model_key, provider_key)
        return (provider_key,)

    def _from_table(self, table: Mapping[str, float], provider: str, model_ref: str | None) -> tuple[str, float] | None:
        for key in self._lookup_keys(provider, model_ref):
            if key in table:
                return key, table[key]
        return None

    def resolve(self, provider: str, model_ref: str | None = None) -> Optional[ProviderCost]:
        provider_key = normalize_provider_key(provider)
        normalized_model = normalize_model_ref(model_ref) if model_ref and str(model_ref).strip() else None

        external = self._from_table(self.external_table, provider_key, normalized_model)
        if external is not None:
            _, ratio = external
            cost = ProviderCost(
                provider=provider_key,
                model_ref=normalized_model,
                cost_ratio=ratio,
                source="external",
                confidence="exact",
            )
            self.cache.set(provider_key, cost, normalized_model)
            return cost

        cached = self.cache.get(provider_key, normalized_model)
        if cached is not None:
            return ProviderCost(
                provider=provider_key,
                model_ref=cached.model_ref or normalized_model,
                cost_ratio=cached.cost_ratio,
                source="cache",
                pricing_unit=cached.pricing_unit,
                confidence=cached.confidence,
            )

        if self.canonical_catalog_rows is not None:
            catalog_entry = resolve_provider_model_cost(
                provider_key=provider_key,
                model_ref=normalized_model,
                catalog_rows=self.canonical_catalog_rows,
            )
            if catalog_entry is not None:
                return ProviderCost(
                    provider=provider_key,
                    model_ref=catalog_entry.model_ref,
                    cost_ratio=catalog_entry.cost_ratio,
                    source="canonical_catalog",
                    pricing_unit=catalog_entry.pricing_unit,
                    confidence="estimated",
                )


        workspace = self._from_table(self.workspace_override, provider_key, normalized_model)
        if workspace is not None:
            key, ratio = workspace
            inferred_model = normalized_model
            if ":" in key:
                inferred_model = key.split(":", 1)[1]
            return ProviderCost(
                provider=provider_key,
                model_ref=inferred_model,
                cost_ratio=ratio,
                source="workspace",
                confidence="fallback",
            )

        return None


def score_cost_ratio(cost_ratio: float | None) -> float:
    if cost_ratio is None:
        return 1.0
    value = float(cost_ratio)
    if value <= 0:
        return 0.0
    return 1.0 / value
