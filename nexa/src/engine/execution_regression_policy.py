"""
execution_regression_policy.py

Regression policy layer.

Evaluates a RegressionResult produced by the detector and determines
the policy decision: PASS, WARN, or FAIL.

This layer sits between the detector and the formatter/CLI.

Architecture:
    contracts / regression_reason_codes
        ↓
    detector  (produces RegressionResult)
        ↓
    policy    (produces PolicyDecision)   ← this module
        ↓
    formatter
        ↓
    CLI

Default policy rules:
    HIGH severity regression  → FAIL
    MEDIUM severity regression → WARN
    LOW severity regression   → PASS (ignored)

Precedence:
    if any HIGH  → FAIL
    else if any MEDIUM → WARN
    else → PASS

Guarantees:
    - Pure function: no mutation of regression objects
    - Deterministic: same input → same output
    - No I/O, no side effects
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from src.engine.execution_regression_detector import (
    REGRESSION_SEVERITY_HIGH,
    REGRESSION_SEVERITY_MEDIUM,
    RegressionResult,
)


# ---------------------------------------------------------------------------
# Policy status constants
# ---------------------------------------------------------------------------

POLICY_STATUS_PASS = "PASS"
POLICY_STATUS_WARN = "WARN"
POLICY_STATUS_FAIL = "FAIL"

VALID_POLICY_STATUSES = frozenset({
    POLICY_STATUS_PASS,
    POLICY_STATUS_WARN,
    POLICY_STATUS_FAIL,
})


# ---------------------------------------------------------------------------
# PolicyDecision dataclass
# ---------------------------------------------------------------------------

@dataclass
class PolicyDecision:
    """Result of policy evaluation against a RegressionResult.

    status:
        PASS  - no actionable regressions
        WARN  - medium severity regressions present
        FAIL  - high severity regressions present

    reasons:
        Human-readable list of explanations for the decision.
    """
    status: str
    reasons: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status not in VALID_POLICY_STATUSES:
            raise ValueError(
                f"Invalid policy status: {self.status!r}. "
                f"Must be one of {sorted(VALID_POLICY_STATUSES)}."
            )


# ---------------------------------------------------------------------------
# Policy evaluation
# ---------------------------------------------------------------------------

def _trigger_line(regression: object) -> str:
    """Build a deterministic trigger line for a single regression.

    Format:
        "Trigger: node <id> (<reason_code>, <severity>)"
        "Trigger: artifact <id> (<reason_code>, <severity>)"
        "Trigger: context <key> (<reason_code>, <severity>)"
    """
    from src.engine.execution_regression_detector import (
        ArtifactRegression,
        ContextRegression,
        NodeRegression,
    )

    if isinstance(regression, NodeRegression):
        return (
            f"Trigger: node {regression.node_id}"
            f" ({regression.reason_code}, {regression.severity})"
        )
    if isinstance(regression, ArtifactRegression):
        return (
            f"Trigger: artifact {regression.artifact_id}"
            f" ({regression.reason_code}, {regression.severity})"
        )
    if isinstance(regression, ContextRegression):
        return (
            f"Trigger: context {regression.context_key}"
            f" ({regression.reason_code}, {regression.severity})"
        )
    return f"Trigger: unknown regression ({regression!r})"


def evaluate_regression_policy(regressions: RegressionResult) -> PolicyDecision:
    """Evaluate regression policy against a RegressionResult.

    Applies default policy rules:
        HIGH   → FAIL
        MEDIUM → WARN
        LOW    → ignored (PASS)

    Precedence: FAIL > WARN > PASS

    Reason format:
        FAIL:
            "FAIL: <N> high severity regression(s) detected"
            "Trigger: node n1 (NODE_SUCCESS_TO_FAILURE, HIGH)"
            ...
        WARN:
            "WARN: <N> medium severity regression(s) detected"
            "Trigger: context ctx.key (CONTEXT_KEY_REMOVED, MEDIUM)"
            ...
        PASS:
            "PASS: no blocking regressions detected"

    Trigger ordering: nodes → artifacts → context (input order within each).

    Args:
        regressions: RegressionResult produced by detect_regressions().

    Returns:
        PolicyDecision with status and detailed human-readable reasons.

    Guarantees:
        - Does not mutate the input.
        - Deterministic: same input → same output.
    """
    # Deterministic order: nodes first, artifacts second, context third
    ordered = (
        list(regressions.nodes)
        + list(regressions.artifacts)
        + list(regressions.context)
    )

    high = [r for r in ordered if r.severity == REGRESSION_SEVERITY_HIGH]
    medium = [r for r in ordered if r.severity == REGRESSION_SEVERITY_MEDIUM]

    if high:
        reasons = [f"FAIL: {len(high)} high severity regression(s) detected"]
        reasons += [_trigger_line(r) for r in high]
        return PolicyDecision(status=POLICY_STATUS_FAIL, reasons=reasons)

    if medium:
        reasons = [f"WARN: {len(medium)} medium severity regression(s) detected"]
        reasons += [_trigger_line(r) for r in medium]
        return PolicyDecision(status=POLICY_STATUS_WARN, reasons=reasons)

    return PolicyDecision(
        status=POLICY_STATUS_PASS,
        reasons=["PASS: no blocking regressions detected"],
    )
