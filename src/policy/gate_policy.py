
from dataclasses import dataclass
from typing import Optional
from src.models.decision_models import Decision


@dataclass
class PolicyDecision:
    decision: Decision
    message: str
    reason_code: str
    stop_reason: Optional[str] = None
    stop_detail: Optional[str] = None


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
