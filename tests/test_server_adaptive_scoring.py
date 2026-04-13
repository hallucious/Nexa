from src.server.adaptive_scoring import AdaptiveWeights, normalize, update_weights


def test_normalize_returns_balanced_defaults_when_total_is_zero() -> None:
    normalized = normalize(AdaptiveWeights(0.0, 0.0, 0.0, 0.0, 0.0))
    assert normalized.health == 0.2
    assert normalized.cost == 0.2
    assert normalized.priority == 0.2
    assert normalized.latency == 0.2
    assert normalized.reliability == 0.2


def test_update_weights_success_increases_runtime_factors() -> None:
    current = AdaptiveWeights(0.2, 0.2, 0.2, 0.2, 0.2)
    updated = update_weights(
        current,
        success=True,
        latency_score=0.8,
        reliability_score=0.9,
    )
    assert updated.latency > 0.2
    assert updated.reliability > 0.2


def test_update_weights_failure_increases_guard_factors() -> None:
    current = AdaptiveWeights(0.2, 0.2, 0.2, 0.2, 0.2)
    updated = update_weights(
        current,
        success=False,
        latency_score=0.8,
        reliability_score=0.9,
    )
    assert updated.health > 0.2
    assert updated.cost > 0.2
