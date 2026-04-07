from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional

from src.engine.change_signal_extractor import ChangeSignal
from src.engine.execution_regression_detector import (
    REGRESSION_SEVERITY_HIGH,
    REGRESSION_SEVERITY_MEDIUM,
    RegressionResult,
)

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

    def __post_init__(self) -> None:
        if self.status not in VALID_POLICY_STATUSES:
            raise ValueError(f"Invalid policy status: {self.status!r}")


def _trigger_line(regression: object) -> str:
    from src.engine.execution_regression_detector import (
        ArtifactRegression,
        ContextRegression,
        NodeRegression,
        VerificationRegression,
    )

    if isinstance(regression, NodeRegression):
        return f"Trigger: node {regression.node_id} ({regression.reason_code}, {regression.severity})"
    if isinstance(regression, ArtifactRegression):
        return f"Trigger: artifact {regression.artifact_id} ({regression.reason_code}, {regression.severity})"
    if isinstance(regression, ContextRegression):
        return f"Trigger: context {regression.context_key} ({regression.reason_code}, {regression.severity})"
    if isinstance(regression, VerificationRegression):
        detail_codes = list(regression.right_reason_codes) or list(regression.left_reason_codes)
        if detail_codes:
            return (
                f"Trigger: {regression.target_type} {regression.target_id} "
                f"({regression.reason_code}, {regression.severity}; verifier_codes={','.join(detail_codes)})"
            )
        return f"Trigger: {regression.target_type} {regression.target_id} ({regression.reason_code}, {regression.severity})"
    return f"Trigger: unknown regression ({regression!r})"


def _apply_override_immutable(regressions, overrides: Dict[str, str]):
    if not overrides:
        return regressions

    updated = []
    for regression in regressions:
        if regression.reason_code in overrides:
            updated.append(replace(regression, severity=overrides[regression.reason_code]))
        else:
            updated.append(regression)
    return updated


def evaluate_regression_policy(regressions: RegressionResult, overrides: Optional[Dict[str, str]] = None) -> PolicyDecision:
    ordered = list(regressions.nodes) + list(regressions.artifacts) + list(regressions.context) + list(regressions.verification)
    ordered = _apply_override_immutable(ordered, overrides or {})

    high = [regression for regression in ordered if regression.severity == REGRESSION_SEVERITY_HIGH]
    medium = [regression for regression in ordered if regression.severity == REGRESSION_SEVERITY_MEDIUM]
    if high:
        reasons = [f"FAIL: {len(high)} high severity regression(s) detected"]
        reasons += [_trigger_line(regression) for regression in high]
        return PolicyDecision(status=POLICY_STATUS_FAIL, reasons=reasons)

    if medium:
        reasons = [f"WARN: {len(medium)} medium severity regression(s) detected"]
        reasons += [_trigger_line(regression) for regression in medium]
        return PolicyDecision(status=POLICY_STATUS_WARN, reasons=reasons)

    return PolicyDecision(status=POLICY_STATUS_PASS, reasons=["PASS: no blocking regressions detected"])


def evaluate_change_signals(signals: List[ChangeSignal]) -> PolicyDecision:
    if not signals:
        return PolicyDecision(status=POLICY_STATUS_PASS, reasons=["PASS: no change signals detected"])

    reasons: List[str] = []
    has_high = False
    has_low = False

    for signal in signals:
        if signal.signal_type == "REPLACE":
            has_high = True
            reasons.append(f'FAIL: signal REPLACE (before="{signal.before}", after="{signal.after}")')
        elif signal.signal_type == "REMOVE":
            has_high = True
            reasons.append(f'FAIL: signal REMOVE (before="{signal.before}")')
        elif signal.signal_type == "ADD":
            has_low = True
            reasons.append(f'WARN: signal ADD (after="{signal.after}")')
        else:
            has_high = True
            reasons.append(f'FAIL: signal UNKNOWN (type="{signal.signal_type}")')

    if has_high:
        return PolicyDecision(status=POLICY_STATUS_FAIL, reasons=reasons)
    if has_low:
        return PolicyDecision(status=POLICY_STATUS_WARN, reasons=reasons)
    return PolicyDecision(status=POLICY_STATUS_PASS, reasons=["PASS: no change signals detected"])


def evaluate_unified_policy(regressions: RegressionResult, signals: List[ChangeSignal], overrides: Optional[Dict[str, str]] = None) -> PolicyDecision:
    regression_decision = evaluate_regression_policy(regressions, overrides)
    signal_decision = evaluate_change_signals(signals)

    if POLICY_STATUS_FAIL in (regression_decision.status, signal_decision.status):
        status = POLICY_STATUS_FAIL
    elif POLICY_STATUS_WARN in (regression_decision.status, signal_decision.status):
        status = POLICY_STATUS_WARN
    else:
        status = POLICY_STATUS_PASS

    return PolicyDecision(status=status, reasons=list(regression_decision.reasons) + list(signal_decision.reasons))
