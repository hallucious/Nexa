from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdaptiveWeights:
    health: float
    cost: float
    priority: float
    latency: float
    reliability: float


def normalize(weights: AdaptiveWeights) -> AdaptiveWeights:
    total = (
        weights.health
        + weights.cost
        + weights.priority
        + weights.latency
        + weights.reliability
    )
    if total <= 0:
        return AdaptiveWeights(
            health=0.2,
            cost=0.2,
            priority=0.2,
            latency=0.2,
            reliability=0.2,
        )
    return AdaptiveWeights(
        health=weights.health / total,
        cost=weights.cost / total,
        priority=weights.priority / total,
        latency=weights.latency / total,
        reliability=weights.reliability / total,
    )


def update_weights(
    current: AdaptiveWeights,
    *,
    success: bool,
    latency_score: float,
    reliability_score: float,
    learning_rate: float = 0.05,
) -> AdaptiveWeights:
    """Return normalized adaptive weights after one recovery outcome.

    This is intentionally small and deterministic. The goal of this batch is to
    introduce a simple weight-adjustment primitive that can later be wired into
    persistence and higher-level policy control.
    """
    latency_score = max(0.0, min(1.0, latency_score))
    reliability_score = max(0.0, min(1.0, reliability_score))
    learning_rate = max(0.0, learning_rate)

    health = current.health
    cost = current.cost
    priority = current.priority
    latency = current.latency
    reliability = current.reliability

    if success:
        reliability += learning_rate * reliability_score
        latency += learning_rate * latency_score
        cost = max(0.0, cost - (learning_rate * 0.5 * latency_score))
    else:
        health += learning_rate
        cost += learning_rate
        reliability = max(0.0, reliability - (learning_rate * 0.5))

    return normalize(
        AdaptiveWeights(
            health=health,
            cost=cost,
            priority=priority,
            latency=latency,
            reliability=reliability,
        )
    )
