"""safety_gate.py

Policy / Safety Gate engine (precision track, v0.1).

Evaluates a request against risk tiers and permission sets.
Engine-owned: policy veto dominates convenience.
Logs all gate decisions for traceability.
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Set

from src.contracts.safety_gate_contract import (
    GateStatus,
    PermissionSet,
    RiskTier,
    SafetyGateError,
    SafetyGateResult,
)


# ── Risk classification ───────────────────────────────────────────────────

# Forbidden action patterns that always escalate to BLOCKED
_BLOCKED_ACTION_PATTERNS: Set[str] = {
    "delete_all",
    "override_policy",
    "bypass_human_approval",
    "unrestricted_file_mutation",
    "mass_data_export",
}

# Patterns that require RESTRICTED handling
_RESTRICTED_ACTION_PATTERNS: Set[str] = {
    "external_api_call",
    "file_mutation",
    "model_override",
    "plugin_privilege_escalation",
}

# Per-tier default status
_TIER_DEFAULT_STATUS: Dict[str, str] = {
    RiskTier.LOW: GateStatus.ALLOW,
    RiskTier.MEDIUM: GateStatus.ALLOW_WITH_REVIEW,
    RiskTier.HIGH: GateStatus.RESTRICT,
    RiskTier.RESTRICTED: GateStatus.RESTRICT,
    RiskTier.BLOCKED: GateStatus.BLOCK,
}


def classify_risk(
    *,
    requested_actions: List[str],
    requested_providers: Optional[List[str]] = None,
    requested_plugins: Optional[List[str]] = None,
    data_sensitivity: str = RiskTier.LOW,
    policy_overrides: Optional[Dict[str, str]] = None,
) -> str:
    """Classify the risk tier of a request.

    Returns one of RiskTier values.  Uses worst-case (highest) tier found.
    """
    current_tier = data_sensitivity if data_sensitivity in RiskTier._ALL else RiskTier.LOW
    tier_rank = RiskTier._ORDERED

    def _upgrade(tier: str, candidate: str) -> str:
        if tier_rank.index(candidate) > tier_rank.index(tier):
            return candidate
        return tier

    for action in (requested_actions or []):
        if action in _BLOCKED_ACTION_PATTERNS:
            return RiskTier.BLOCKED  # immediate short-circuit
        if action in _RESTRICTED_ACTION_PATTERNS:
            current_tier = _upgrade(current_tier, RiskTier.RESTRICTED)

    # Policy overrides (per-action explicit tier)
    for action in (requested_actions or []):
        override = (policy_overrides or {}).get(action)
        if override and override in RiskTier._ALL:
            current_tier = _upgrade(current_tier, override)

    return current_tier


def evaluate_gate(
    *,
    target_ref: str,
    requested_actions: List[str],
    permission_set: Optional[PermissionSet] = None,
    requested_providers: Optional[List[str]] = None,
    requested_plugins: Optional[List[str]] = None,
    data_sensitivity: str = RiskTier.LOW,
    policy_overrides: Optional[Dict[str, str]] = None,
    gate_id: Optional[str] = None,
) -> SafetyGateResult:
    """Evaluate the safety gate for a request.

    Returns a SafetyGateResult.  Blocked results must not proceed to execution.
    """
    ps = permission_set or PermissionSet()

    risk_tier = classify_risk(
        requested_actions=requested_actions,
        requested_providers=requested_providers,
        requested_plugins=requested_plugins,
        data_sensitivity=data_sensitivity,
        policy_overrides=policy_overrides,
    )

    reason_codes: List[str] = []
    blocked_actions: List[str] = []
    final_allowed: List[str] = []
    required_reviews: List[str] = []

    # Evaluate each requested action
    for action in requested_actions:
        if action in _BLOCKED_ACTION_PATTERNS:
            blocked_actions.append(action)
            reason_codes.append(f"ACTION_BLOCKED:{action}")
        elif action in ps.denied_actions:
            blocked_actions.append(action)
            reason_codes.append(f"PERMISSION_DENIED:{action}")
        elif ps.allowed_actions and action not in ps.allowed_actions:
            blocked_actions.append(action)
            reason_codes.append(f"ACTION_NOT_IN_ALLOWLIST:{action}")
        else:
            final_allowed.append(action)

    # Provider permission check
    for prov in (requested_providers or []):
        if prov in ps.denied_providers:
            reason_codes.append(f"PROVIDER_DENIED:{prov}")
            if risk_tier not in (RiskTier.RESTRICTED, RiskTier.BLOCKED):
                risk_tier = RiskTier.RESTRICTED

    # Plugin permission check
    for plug in (requested_plugins or []):
        if plug in ps.denied_plugins:
            reason_codes.append(f"PLUGIN_DENIED:{plug}")

    # Determine gate status
    status = _TIER_DEFAULT_STATUS[risk_tier]

    # Blocked actions force BLOCK regardless of tier
    if blocked_actions:
        status = GateStatus.BLOCK
        reason_codes.append("BLOCKED_ACTIONS_PRESENT")

    # Human approval required by permission set
    if ps.requires_human_approval:
        required_reviews.append("human_approval")
        reason_codes.append("PERMISSION_REQUIRES_HUMAN_APPROVAL")
        if status == GateStatus.ALLOW:
            status = GateStatus.ALLOW_WITH_REVIEW

    if not reason_codes:
        reason_codes.append(f"RISK_TIER_{risk_tier.upper()}_DEFAULT")

    explanation = (
        f"risk_tier={risk_tier}; status={status}; "
        f"blocked={len(blocked_actions)}; allowed={len(final_allowed)}"
    )

    return SafetyGateResult(
        gate_id=gate_id or str(uuid.uuid4()),
        target_ref=target_ref,
        risk_tier=risk_tier,
        status=status,
        reason_codes=reason_codes,
        blocked_actions=blocked_actions,
        allowed_actions=final_allowed,
        required_reviews=required_reviews,
        explanation=explanation,
    )
