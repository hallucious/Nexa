
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.models.decision_models import Decision
from src.pipeline.stop_reason import StopReason


@dataclass
class PolicyDecision:
    decision: Decision
    message: str
    reason_code: str
    stop_reason: Optional[str] = None
    stop_detail: Optional[str] = None


# -----------------------------
# G1: Design
# -----------------------------
def evaluate_g1(*, violations_count: int) -> PolicyDecision:
    if violations_count > 0:
        return PolicyDecision(
            decision=Decision.FAIL,
            message="Design violations detected",
            reason_code="G1_SELF_CHECK_FAILED",
        )

    return PolicyDecision(
        decision=Decision.PASS,
        message="Design skeleton generated",
        reason_code="OK",
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
            reason_code="G2_BASELINE_KEYS_REMOVED",
        )

    if semantic_attempted and semantic_verdict == "UNKNOWN":
        return PolicyDecision(
            decision=Decision.STOP,
            message="Provider available but semantic verdict UNKNOWN",
            reason_code="G2_SEMANTIC_UNKNOWN_WITH_PROVIDER",
            stop_reason="UNKNOWN",
            stop_detail="G2_SEMANTIC_UNKNOWN_WITH_PROVIDER",
        )

    if semantic_verdict in ("DRIFT", "VIOLATION"):
        return PolicyDecision(
            decision=Decision.FAIL,
            message=f"Semantic continuity failed: {semantic_verdict}",
            reason_code=f"G2_SEMANTIC_{semantic_verdict}",
        )

    return PolicyDecision(
        decision=Decision.PASS,
        message="Continuity OK",
        reason_code="OK",
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
            reason_code="G3_PROVIDER_ERROR",
            stop_reason=StopReason.PROVIDER_ERROR.value,
            stop_detail=stop_error,
        )

    if fail_reasons_count > 0:
        return PolicyDecision(
            decision=Decision.FAIL,
            message="Fact audit completed",
            reason_code="G3_FACT_ERROR",
        )

    return PolicyDecision(
        decision=Decision.PASS,
        message="Fact audit completed",
        reason_code="OK",
    )


# -----------------------------
# G4: Self-check
# -----------------------------
def evaluate_g4(*, prereq_missing: bool, schema_ok: bool) -> PolicyDecision:
    if prereq_missing:
        return PolicyDecision(
            decision=Decision.FAIL,
            message="PREREQ_MISSING",
            reason_code="G4_PREREQ_MISSING",
        )

    if not schema_ok:
        return PolicyDecision(
            decision=Decision.FAIL,
            message="SCHEMA_INVALID",
            reason_code="G4_SCHEMA_INVALID",
        )

    return PolicyDecision(
        decision=Decision.PASS,
        message="OK",
        reason_code="OK",
    )


# -----------------------------
# G5: Implement & test
# -----------------------------
def evaluate_g5(*, timed_out: bool, returncode: int) -> PolicyDecision:
    if (not timed_out) and returncode == 0:
        return PolicyDecision(
            decision=Decision.PASS,
            message="Tests passed.",
            reason_code="OK",
        )

    if timed_out:
        return PolicyDecision(
            decision=Decision.FAIL,
            message="Tests timed out.",
            reason_code="G5_TIMEOUT",
        )

    return PolicyDecision(
        decision=Decision.FAIL,
        message=f"Tests failed (rc={returncode}).",
        reason_code="G5_TEST_FAILED",
    )


# -----------------------------
# G6: Counterfactual review
# -----------------------------
def evaluate_g6(*, conflicts_count: int) -> PolicyDecision:
    if conflicts_count > 0:
        return PolicyDecision(
            decision=Decision.FAIL,
            message=f"{conflicts_count} issue(s) detected.",
            reason_code="G6_COUNTERFACTUAL_CONFLICT",
        )

    return PolicyDecision(
        decision=Decision.PASS,
        message="No counterfactual issues detected.",
        reason_code="OK",
    )
