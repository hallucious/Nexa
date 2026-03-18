from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from src.models.decision_models import Decision
from src.policy.stop_reason import StopReason
from src.policy.reason_codes import ReasonCode


@dataclass
class PolicyDecision:
    decision: Decision
    message: str
    reason_code: str
    stop_reason: Optional[str] = None
    stop_detail: Optional[str] = None
    reason_trace: List[str] = field(default_factory=list)


# -----------------------------
# G1: Design
# -----------------------------
def evaluate_g1(*, violations_count: int) -> PolicyDecision:
    if violations_count > 0:
        return PolicyDecision(
            decision=Decision.FAIL,
            message="Design violations detected",
            reason_code=ReasonCode.G1_SELF_CHECK_FAILED.value,
        )

    return PolicyDecision(
        decision=Decision.PASS,
        message="Design skeleton generated",
        reason_code=ReasonCode.OK.value,
    )


# -----------------------------
# G2: Continuity
# -----------------------------
def evaluate_g2(
    *,
    structure_removed: bool,
    semantic_attempted: bool,
    semantic_verdict: str,
) -> PolicyDecision:
    if structure_removed:
        return PolicyDecision(
            decision=Decision.FAIL,
            message="Removed baseline fields",
            reason_code=ReasonCode.G2_BASELINE_KEYS_REMOVED.value,
        )

    if semantic_attempted and semantic_verdict == "UNKNOWN":
        return PolicyDecision(
            decision=Decision.STOP,
            message="Provider available but semantic verdict UNKNOWN",
            reason_code=ReasonCode.G2_SEMANTIC_UNKNOWN_WITH_PROVIDER.value,
            stop_reason="UNKNOWN",
            stop_detail="G2_SEMANTIC_UNKNOWN_WITH_PROVIDER",
        )

    if semantic_verdict == "DRIFT":
        return PolicyDecision(
            decision=Decision.FAIL,
            message="Semantic continuity failed: DRIFT",
            reason_code=ReasonCode.G2_SEMANTIC_DRIFT.value,
        )

    if semantic_verdict == "VIOLATION":
        return PolicyDecision(
            decision=Decision.FAIL,
            message="Semantic continuity failed: VIOLATION",
            reason_code=ReasonCode.G2_SEMANTIC_VIOLATION.value,
        )

    return PolicyDecision(
        decision=Decision.PASS,
        message="Continuity OK",
        reason_code=ReasonCode.OK.value,
    )


# -----------------------------
# G3: Fact audit
# -----------------------------
def evaluate_g3(
    *,
    stop_error: str,
    fail_reasons_count: int,
) -> PolicyDecision:
    if stop_error:
        return PolicyDecision(
            decision=Decision.STOP,
            message="Fact audit completed",
            reason_code=ReasonCode.G3_PROVIDER_ERROR.value,
            stop_reason=StopReason.PROVIDER_ERROR.value,
            stop_detail=stop_error,
        )

    if fail_reasons_count > 0:
        return PolicyDecision(
            decision=Decision.FAIL,
            message="Fact audit completed",
            reason_code=ReasonCode.G3_FACT_ERROR.value,
        )

    return PolicyDecision(
        decision=Decision.PASS,
        message="Fact audit completed",
        reason_code=ReasonCode.OK.value,
    )


# -----------------------------
# G4: Self-check
# -----------------------------
def evaluate_g4(*, prereq_missing: bool, schema_ok: bool) -> PolicyDecision:
    if prereq_missing:
        return PolicyDecision(
            decision=Decision.FAIL,
            message="PREREQ_MISSING",
            reason_code=ReasonCode.G4_PREREQ_MISSING.value,
        )

    if not schema_ok:
        return PolicyDecision(
            decision=Decision.FAIL,
            message="SCHEMA_INVALID",
            reason_code=ReasonCode.G4_SCHEMA_INVALID.value,
        )

    return PolicyDecision(
        decision=Decision.PASS,
        message="OK",
        reason_code=ReasonCode.OK.value,
    )


# -----------------------------
# G5: Implement & test
# -----------------------------
def evaluate_g5(*, timed_out: bool, returncode: int) -> PolicyDecision:
    if (not timed_out) and returncode == 0:
        return PolicyDecision(
            decision=Decision.PASS,
            message="Tests passed.",
            reason_code=ReasonCode.OK.value,
        )

    if timed_out:
        return PolicyDecision(
            decision=Decision.FAIL,
            message="Tests timed out.",
            reason_code=ReasonCode.G5_TIMEOUT.value,
        )

    return PolicyDecision(
        decision=Decision.FAIL,
        message=f"Tests failed (rc={returncode}).",
        reason_code=ReasonCode.G5_TEST_FAILED.value,
    )


# -----------------------------
# G6: Counterfactual review
# -----------------------------
def evaluate_g6(*, conflicts_count: int) -> PolicyDecision:
    if conflicts_count > 0:
        return PolicyDecision(
            decision=Decision.FAIL,
            message=f"{conflicts_count} issue(s) detected.",
            reason_code=ReasonCode.G6_COUNTERFACTUAL_CONFLICT.value,
        )

    return PolicyDecision(
        decision=Decision.PASS,
        message="No counterfactual issues detected.",
        reason_code=ReasonCode.OK.value,
    )


# -----------------------------
# G7: Final review
# -----------------------------
def evaluate_g7(*, prereq_missing: bool) -> PolicyDecision:
    if prereq_missing:
        return PolicyDecision(
            decision=Decision.FAIL,
            message="Final review prerequisite missing.",
            reason_code=ReasonCode.G7_PREREQ_MISSING.value,
        )

    return PolicyDecision(
        decision=Decision.PASS,
        message="Final review passed.",
        reason_code=ReasonCode.OK.value,
    )
