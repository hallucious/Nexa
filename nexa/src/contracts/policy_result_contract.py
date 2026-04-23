"""
policy_result_contract.py

Shared policy result types consumed by multiple layers:
  engine  — produces PolicyDecision from regression evaluation
  engine  — produces ExplainabilityResult from policy explainability
  ui      — renders validation panel using both types

Placing these types in contracts removes the ui → engine type dependency
while leaving the business logic (evaluate_regression_policy,
build_explainability) in the engine where it belongs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


POLICY_STATUS_PASS = "PASS"
POLICY_STATUS_WARN = "WARN"
POLICY_STATUS_FAIL = "FAIL"

VALID_POLICY_STATUSES = frozenset({
    POLICY_STATUS_PASS,
    POLICY_STATUS_WARN,
    POLICY_STATUS_FAIL,
})


@dataclass
class PolicyDecision:
    status: str
    reasons: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in VALID_POLICY_STATUSES:
            raise ValueError(f"Invalid policy status: {self.status!r}")


@dataclass(frozen=True)
class ExplainabilityResult:
    status: str
    summary: str
    categories: Dict[str, List[str]]
    verification_contracts: List[str] = field(default_factory=list)


__all__ = [
    "POLICY_STATUS_PASS",
    "POLICY_STATUS_WARN",
    "POLICY_STATUS_FAIL",
    "VALID_POLICY_STATUSES",
    "PolicyDecision",
    "ExplainabilityResult",
]
