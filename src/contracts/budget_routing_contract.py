"""budget_routing_contract.py

Typed contract for Budget-Aware Routing (precision track, v0.1).

Canonical objects:
  - RoutingContext
  - FallbackPlan
  - RouteDecision
  - RouteLog

These define the input/output surface for the budget router.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class RouteTier:
    CHEAP = "cheap"
    BALANCED = "balanced"
    HIGH_QUALITY = "high_quality"
    HIGH_SAFETY = "high_safety"

    _ALL = {CHEAP, BALANCED, HIGH_QUALITY, HIGH_SAFETY}


class RiskLevel:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    RESTRICTED = "restricted"

    _ALL = {LOW, MEDIUM, HIGH, RESTRICTED}


class BudgetRoutingError(ValueError):
    """Raised when budget routing contract invariants are violated."""


@dataclass(frozen=True)
class RoutingContext:
    node_id: str
    task_type: str
    current_budget: float          # remaining budget in cost units
    difficulty_estimate: float     # 0.0–1.0
    risk_level: str                # RiskLevel
    allowed_providers: List[str]
    preferred_route_tier: Optional[str] = None
    latency_target: Optional[float] = None   # seconds
    quality_target: Optional[float] = None   # 0.0–1.0
    retry_count: int = 0
    prior_failures: List[str] = field(default_factory=list)
    safety_requirements: List[str] = field(default_factory=list)
    allowed_models: List[str] = field(default_factory=list)
    allowed_plugins: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.node_id:
            raise BudgetRoutingError("node_id must be non-empty")
        if not self.task_type:
            raise BudgetRoutingError("task_type must be non-empty")
        if self.current_budget < 0:
            raise BudgetRoutingError("current_budget must be non-negative")
        if not (0.0 <= self.difficulty_estimate <= 1.0):
            raise BudgetRoutingError("difficulty_estimate must be in [0.0, 1.0]")
        if self.risk_level not in RiskLevel._ALL:
            raise BudgetRoutingError(f"unsupported risk_level: {self.risk_level!r}")
        if self.preferred_route_tier is not None and self.preferred_route_tier not in RouteTier._ALL:
            raise BudgetRoutingError(f"unsupported preferred_route_tier: {self.preferred_route_tier!r}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "task_type": self.task_type,
            "current_budget": self.current_budget,
            "difficulty_estimate": self.difficulty_estimate,
            "risk_level": self.risk_level,
            "preferred_route_tier": self.preferred_route_tier,
            "latency_target": self.latency_target,
            "quality_target": self.quality_target,
            "retry_count": self.retry_count,
            "prior_failures": list(self.prior_failures),
            "safety_requirements": list(self.safety_requirements),
            "allowed_providers": list(self.allowed_providers),
            "allowed_models": list(self.allowed_models),
            "allowed_plugins": list(self.allowed_plugins),
        }


@dataclass(frozen=True)
class FallbackPlan:
    enabled: bool
    fallback_route_ids: List[str] = field(default_factory=list)
    escalation_rules: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "fallback_route_ids": list(self.fallback_route_ids),
            "escalation_rules": list(self.escalation_rules),
        }


@dataclass(frozen=True)
class RouteDecision:
    route_id: str
    selected_provider_id: str
    selected_route_tier: str
    estimated_cost: float
    estimated_latency: float
    selection_reason_codes: List[str]
    explanation: str
    fallback_plan: FallbackPlan
    selected_model_id: Optional[str] = None
    selected_plugins: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.route_id:
            raise BudgetRoutingError("route_id must be non-empty")
        if not self.selected_provider_id:
            raise BudgetRoutingError("selected_provider_id must be non-empty")
        if self.selected_route_tier not in RouteTier._ALL:
            raise BudgetRoutingError(
                f"unsupported route_tier: {self.selected_route_tier!r}"
            )
        if self.estimated_cost < 0:
            raise BudgetRoutingError("estimated_cost must be non-negative")
        if self.estimated_latency < 0:
            raise BudgetRoutingError("estimated_latency must be non-negative")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "route_id": self.route_id,
            "selected_provider_id": self.selected_provider_id,
            "selected_model_id": self.selected_model_id,
            "selected_plugins": list(self.selected_plugins),
            "estimated_cost": self.estimated_cost,
            "estimated_latency": self.estimated_latency,
            "selected_route_tier": self.selected_route_tier,
            "selection_reason_codes": list(self.selection_reason_codes),
            "fallback_plan": self.fallback_plan.to_dict(),
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class RouteLog:
    """Immutable log of a routing decision for audit and analysis."""
    log_id: str
    route_decision: RouteDecision
    routing_context: RoutingContext
    verifier_contradicted: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "route_decision": self.route_decision.to_dict(),
            "routing_context": self.routing_context.to_dict(),
            "verifier_contradicted": self.verifier_contradicted,
            "notes": self.notes,
        }
