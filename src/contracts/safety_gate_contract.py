"""safety_gate_contract.py

Typed contract for the Policy / Safety Gate (precision track, v0.1).

Canonical objects:
  - SafetyGateResult
  - PermissionSet

Risk tiers: low / medium / high / restricted / blocked
Gate statuses: allow / allow_with_review / restrict / block
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class RiskTier:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"

    _ALL = {LOW, MEDIUM, HIGH, RESTRICTED, BLOCKED}
    _ORDERED = [LOW, MEDIUM, HIGH, RESTRICTED, BLOCKED]


class GateStatus:
    ALLOW = "allow"
    ALLOW_WITH_REVIEW = "allow_with_review"
    RESTRICT = "restrict"
    BLOCK = "block"

    _ALL = {ALLOW, ALLOW_WITH_REVIEW, RESTRICT, BLOCK}


class SafetyGateError(ValueError):
    """Raised when safety gate contract invariants are violated."""


@dataclass(frozen=True)
class PermissionSet:
    """Explicit permission declarations for a node/action."""
    allowed_providers: List[str] = field(default_factory=list)
    allowed_plugins: List[str] = field(default_factory=list)
    allowed_actions: List[str] = field(default_factory=list)
    denied_providers: List[str] = field(default_factory=list)
    denied_plugins: List[str] = field(default_factory=list)
    denied_actions: List[str] = field(default_factory=list)
    requires_human_approval: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed_providers": list(self.allowed_providers),
            "allowed_plugins": list(self.allowed_plugins),
            "allowed_actions": list(self.allowed_actions),
            "denied_providers": list(self.denied_providers),
            "denied_plugins": list(self.denied_plugins),
            "denied_actions": list(self.denied_actions),
            "requires_human_approval": self.requires_human_approval,
        }


@dataclass(frozen=True)
class SafetyGateResult:
    gate_id: str
    target_ref: str
    risk_tier: str
    status: str
    reason_codes: List[str]
    blocked_actions: List[str]
    allowed_actions: List[str]
    required_reviews: List[str]
    explanation: str

    def __post_init__(self) -> None:
        if not self.gate_id:
            raise SafetyGateError("gate_id must be non-empty")
        if not self.target_ref:
            raise SafetyGateError("target_ref must be non-empty")
        if self.risk_tier not in RiskTier._ALL:
            raise SafetyGateError(f"unsupported risk_tier: {self.risk_tier!r}")
        if self.status not in GateStatus._ALL:
            raise SafetyGateError(f"unsupported gate status: {self.status!r}")

    @property
    def is_blocked(self) -> bool:
        return self.status == GateStatus.BLOCK

    @property
    def requires_review(self) -> bool:
        return self.status in (GateStatus.ALLOW_WITH_REVIEW, GateStatus.RESTRICT)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "target_ref": self.target_ref,
            "risk_tier": self.risk_tier,
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "blocked_actions": list(self.blocked_actions),
            "allowed_actions": list(self.allowed_actions),
            "required_reviews": list(self.required_reviews),
            "explanation": self.explanation,
        }
