from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

_ALLOWED_STATUSES = {"pass", "warning", "fail", "inconclusive"}
_ALLOWED_SEVERITIES = {"info", "warning", "error", "critical"}
_ALLOWED_VERIFIER_TYPES = {
    "structural",
    "logical",
    "requirement",
    "policy",
    "evidence",
    "composite",
}


@dataclass(frozen=True)
class RetryAdvice:
    should_retry: bool = False
    strategy: Optional[str] = None
    reason: Optional[str] = None


@dataclass(frozen=True)
class BranchAdvice:
    should_branch: bool = False
    reason: Optional[str] = None


@dataclass(frozen=True)
class EscalationAdvice:
    should_escalate: bool = False
    target: Optional[str] = None
    reason: Optional[str] = None


@dataclass(frozen=True)
class VerifierFinding:
    finding_id: str
    severity: str
    category: str
    reason_code: str
    message: str
    evidence_refs: list[str] = field(default_factory=list)
    suggested_action: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.finding_id:
            raise ValueError("VerifierFinding.finding_id must be non-empty")
        if self.severity not in _ALLOWED_SEVERITIES:
            raise ValueError(f"unsupported finding severity: {self.severity}")
        if not self.category:
            raise ValueError("VerifierFinding.category must be non-empty")
        if not self.reason_code:
            raise ValueError("VerifierFinding.reason_code must be non-empty")
        if not self.message:
            raise ValueError("VerifierFinding.message must be non-empty")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerifierResult:
    verifier_id: str
    verifier_type: str
    target_ref: str
    status: str
    reason_code: str
    findings: list[VerifierFinding] = field(default_factory=list)
    explanation: str = ""
    score: Optional[float] = None
    confidence: Optional[float] = None
    retry_advice: RetryAdvice = field(default_factory=RetryAdvice)
    branch_advice: BranchAdvice = field(default_factory=BranchAdvice)
    escalation_advice: EscalationAdvice = field(default_factory=EscalationAdvice)

    def __post_init__(self) -> None:
        if not self.verifier_id:
            raise ValueError("VerifierResult.verifier_id must be non-empty")
        if self.verifier_type not in _ALLOWED_VERIFIER_TYPES:
            raise ValueError(f"unsupported verifier_type: {self.verifier_type}")
        if not self.target_ref:
            raise ValueError("VerifierResult.target_ref must be non-empty")
        if self.status not in _ALLOWED_STATUSES:
            raise ValueError(f"unsupported verifier status: {self.status}")
        if not self.reason_code:
            raise ValueError("VerifierResult.reason_code must be non-empty")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompositeVerifierResult:
    target_ref: str
    constituent_results: list[VerifierResult] = field(default_factory=list)
    aggregate_status: str = "inconclusive"
    aggregate_score: Optional[float] = None
    aggregate_confidence: Optional[float] = None
    blocking_reason_codes: list[str] = field(default_factory=list)
    recommended_next_step: str = "continue"

    def __post_init__(self) -> None:
        if not self.target_ref:
            raise ValueError("CompositeVerifierResult.target_ref must be non-empty")
        if self.aggregate_status not in _ALLOWED_STATUSES:
            raise ValueError(f"unsupported aggregate_status: {self.aggregate_status}")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
