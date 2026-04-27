from src.server.pricing_cache import PricingCache
from src.server.pricing_models import ProviderCost
from src.server.pricing_resolver import PricingResolver


def test_external_priority() -> None:
    resolver = PricingResolver(
        external_table={"openai": 1.0},
        cache=PricingCache(),
    )
    cost = resolver.resolve("openai")
    assert cost is not None
    assert cost.source == "external"
    assert cost.cost_ratio == 1.0


def test_cache_fallback() -> None:
    cache = PricingCache()
    cache.set("openai", ProviderCost(provider="openai", cost_ratio=1.1, source="external"))
    resolver = PricingResolver({}, cache)
    cost = resolver.resolve("openai")
    assert cost is not None
    assert cost.source == "cache"
    assert cost.cost_ratio == 1.1


def test_workspace_fallback() -> None:
    resolver = PricingResolver(
        external_table={},
        cache=PricingCache(),
        workspace_override={"claude": 1.5},
    )
    cost = resolver.resolve("claude")
    assert cost is not None
    assert cost.source == "workspace"
    assert cost.cost_ratio == 1.5


def test_unknown_provider_returns_none() -> None:
    resolver = PricingResolver(
        external_table={},
        cache=PricingCache(),
        workspace_override={},
    )
    assert resolver.resolve("unknown") is None



def test_canonical_catalog_model_cost_is_available_when_supplied() -> None:
    from src.server.provider_catalog_runtime import default_provider_model_catalog_rows

    resolver = PricingResolver(
        external_table={},
        cache=PricingCache(),
        canonical_catalog_rows=default_provider_model_catalog_rows(),
    )

    cost = resolver.resolve("openai", "gpt-4o")

    assert cost is not None
    assert cost.source == "canonical_catalog"
    assert cost.provider == "openai"
    assert cost.model_ref == "gpt-4o"
    assert cost.cost_ratio == 3.0
