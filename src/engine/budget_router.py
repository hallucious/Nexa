"""budget_router.py

Budget-Aware Routing engine (precision track, v0.1).

Deterministic, config-driven routing. No random selection.

Route tier selection logic:
  1. If risk_level is RESTRICTED → HIGH_SAFETY tier only.
  2. If difficulty_estimate >= 0.75 or quality_target >= 0.8 → HIGH_QUALITY.
  3. If budget is very tight (< cheap_threshold) → CHEAP.
  4. Otherwise → BALANCED.

Retry escalation:
  - retry_count > 0 escalates one tier upward (cheap→balanced, balanced→high_quality).
  - retry_count > 1 and still failing → HIGH_SAFETY if safety requirements present.
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Tuple

from src.contracts.budget_routing_contract import (
    BudgetRoutingError,
    FallbackPlan,
    RouteDecision,
    RouteLog,
    RouteTier,
    RoutingContext,
    RiskLevel,
)


# ── Tier cost/latency estimates (approximate, deterministic) ──────────────

_TIER_PROFILES: Dict[str, Tuple[float, float]] = {
    # tier → (estimated_cost_units, estimated_latency_seconds)
    RouteTier.CHEAP: (1.0, 1.0),
    RouteTier.BALANCED: (3.0, 2.0),
    RouteTier.HIGH_QUALITY: (8.0, 4.0),
    RouteTier.HIGH_SAFETY: (12.0, 6.0),
}

_TIER_ORDER = [RouteTier.CHEAP, RouteTier.BALANCED, RouteTier.HIGH_QUALITY, RouteTier.HIGH_SAFETY]


def _escalate_tier(tier: str, steps: int = 1) -> str:
    idx = _TIER_ORDER.index(tier)
    return _TIER_ORDER[min(idx + steps, len(_TIER_ORDER) - 1)]


def _select_tier(ctx: RoutingContext) -> Tuple[str, List[str]]:
    """Deterministically select a route tier from context. Returns (tier, reason_codes)."""
    reason_codes: List[str] = []

    # 1. Restricted risk always → HIGH_SAFETY
    if ctx.risk_level == RiskLevel.RESTRICTED:
        reason_codes.append("RISK_RESTRICTED_REQUIRES_HIGH_SAFETY")
        return RouteTier.HIGH_SAFETY, reason_codes

    # 2. Safety requirements present → at least BALANCED
    base_tier = RouteTier.BALANCED
    if ctx.difficulty_estimate >= 0.75:
        base_tier = RouteTier.HIGH_QUALITY
        reason_codes.append("HIGH_DIFFICULTY_REQUIRES_QUALITY")
    if ctx.quality_target is not None and ctx.quality_target >= 0.8:
        base_tier = RouteTier.HIGH_QUALITY
        reason_codes.append("QUALITY_TARGET_REQUIRES_HIGH_QUALITY")

    # 3. Budget too tight for selected tier → downgrade
    cost_estimate = _TIER_PROFILES[base_tier][0]
    if ctx.current_budget < cost_estimate and ctx.current_budget >= _TIER_PROFILES[RouteTier.CHEAP][0]:
        if base_tier != RouteTier.CHEAP:
            reason_codes.append("BUDGET_CONSTRAINED_DOWNGRADE")
            base_tier = RouteTier.CHEAP

    if ctx.current_budget < _TIER_PROFILES[RouteTier.CHEAP][0]:
        reason_codes.append("BUDGET_EXHAUSTED")
        base_tier = RouteTier.CHEAP  # best-effort cheap route; caller handles exhaustion

    # 4. Retry escalation
    if ctx.retry_count == 1:
        base_tier = _escalate_tier(base_tier, 1)
        reason_codes.append("RETRY_ESCALATION_TIER_UP")
    elif ctx.retry_count > 1 and ctx.safety_requirements:
        base_tier = RouteTier.HIGH_SAFETY
        reason_codes.append("REPEATED_RETRY_SAFETY_ESCALATION")

    if not reason_codes:
        reason_codes.append("STANDARD_BALANCED_ROUTING")

    return base_tier, reason_codes


def _select_provider(ctx: RoutingContext, tier: str) -> str:
    """Pick the best allowed provider for the tier (deterministic: first in list)."""
    if not ctx.allowed_providers:
        raise BudgetRoutingError(
            f"no allowed_providers for node {ctx.node_id!r}"
        )
    # Prefer first provider; in a real system this would use registry scoring.
    return ctx.allowed_providers[0]


def decide_route(ctx: RoutingContext) -> RouteDecision:
    """Produce a deterministic RouteDecision from a RoutingContext."""
    tier, reason_codes = _select_tier(ctx)
    cost, latency = _TIER_PROFILES[tier]
    provider_id = _select_provider(ctx, tier)

    # Fallback: arm if higher tier available and budget permits escalation
    fallback_enabled = tier in (RouteTier.CHEAP, RouteTier.BALANCED)
    fallback_route_ids: List[str] = []
    escalation_rules: List[str] = []
    if fallback_enabled:
        next_tier = _escalate_tier(tier, 1)
        fallback_route_ids.append(f"fallback:{next_tier}")
        escalation_rules.append(f"verifier_fail→{next_tier}")

    fallback = FallbackPlan(
        enabled=fallback_enabled,
        fallback_route_ids=fallback_route_ids,
        escalation_rules=escalation_rules,
    )

    explanation = (
        f"tier={tier}; provider={provider_id}; "
        f"difficulty={ctx.difficulty_estimate:.2f}; "
        f"budget={ctx.current_budget:.2f}; "
        f"retry={ctx.retry_count}"
    )

    return RouteDecision(
        route_id=str(uuid.uuid4()),
        selected_provider_id=provider_id,
        selected_model_id=ctx.allowed_models[0] if ctx.allowed_models else None,
        selected_plugins=list(ctx.allowed_plugins),
        estimated_cost=cost,
        estimated_latency=latency,
        selected_route_tier=tier,
        selection_reason_codes=reason_codes,
        fallback_plan=fallback,
        explanation=explanation,
    )


def log_route(
    decision: RouteDecision,
    ctx: RoutingContext,
    *,
    verifier_contradicted: bool = False,
    notes: str = "",
) -> RouteLog:
    """Produce an immutable RouteLog from a completed routing decision."""
    return RouteLog(
        log_id=str(uuid.uuid4()),
        route_decision=decision,
        routing_context=ctx,
        verifier_contradicted=verifier_contradicted,
        notes=notes,
    )
