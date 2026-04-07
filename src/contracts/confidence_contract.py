"""confidence_contract.py

Typed contract for the Uncertainty / Confidence Model (precision track, v0.1).

Canonical objects:
  - ConfidenceBasis
  - ThresholdDecision
  - ConfidenceAssessment

These are append-only output types; never mutate an existing assessment.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ── Enums (str-compatible for JSON persistence) ────────────────────────────


class BasisType:
    EVIDENCE = "evidence"
    VERIFIER = "verifier"
    AGREEMENT = "agreement"
    HISTORY = "history"
    HEURISTIC = "heuristic"

    _ALL = {EVIDENCE, VERIFIER, AGREEMENT, HISTORY, HEURISTIC}


class ThresholdBand:
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CRITICAL_LOW = "critical_low"

    _ALL = {HIGH, MEDIUM, LOW, CRITICAL_LOW}


class RecommendedAction:
    CONTINUE = "continue"
    VERIFY_MORE = "verify_more"
    BRANCH = "branch"
    REROUTE = "reroute"
    HUMAN_REVIEW = "human_review"
    STOP = "stop"

    _ALL = {CONTINUE, VERIFY_MORE, BRANCH, REROUTE, HUMAN_REVIEW, STOP}


class ConfidenceContractError(ValueError):
    """Raised when confidence contract invariants are violated."""


# ── Core dataclasses ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class ConfidenceBasis:
    basis_type: str
    source_ref: str
    contribution_weight: float
    note: Optional[str] = None

    def __post_init__(self) -> None:
        if self.basis_type not in BasisType._ALL:
            raise ConfidenceContractError(
                f"unsupported basis_type: {self.basis_type!r}"
            )
        if not self.source_ref:
            raise ConfidenceContractError("source_ref must be non-empty")
        if not (0.0 <= self.contribution_weight <= 1.0):
            raise ConfidenceContractError(
                "contribution_weight must be in [0.0, 1.0]"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "basis_type": self.basis_type,
            "source_ref": self.source_ref,
            "contribution_weight": self.contribution_weight,
            "note": self.note,
        }


@dataclass(frozen=True)
class ThresholdDecision:
    threshold_band: str
    recommended_action: str
    blocking: bool

    def __post_init__(self) -> None:
        if self.threshold_band not in ThresholdBand._ALL:
            raise ConfidenceContractError(
                f"unsupported threshold_band: {self.threshold_band!r}"
            )
        if self.recommended_action not in RecommendedAction._ALL:
            raise ConfidenceContractError(
                f"unsupported recommended_action: {self.recommended_action!r}"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threshold_band": self.threshold_band,
            "recommended_action": self.recommended_action,
            "blocking": self.blocking,
        }


@dataclass(frozen=True)
class ConfidenceAssessment:
    assessment_id: str
    target_ref: str
    confidence_score: float
    uncertainty_score: float
    evidence_density_score: float
    threshold_decision: ThresholdDecision
    explanation: str
    confidence_basis: List[ConfidenceBasis] = field(default_factory=list)
    agreement_score: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.assessment_id:
            raise ConfidenceContractError("assessment_id must be non-empty")
        if not self.target_ref:
            raise ConfidenceContractError("target_ref must be non-empty")
        for attr in ("confidence_score", "uncertainty_score", "evidence_density_score"):
            val = getattr(self, attr)
            if not (0.0 <= val <= 1.0):
                raise ConfidenceContractError(
                    f"{attr} must be in [0.0, 1.0]; got {val}"
                )
        if self.agreement_score is not None and not (
            0.0 <= self.agreement_score <= 1.0
        ):
            raise ConfidenceContractError("agreement_score must be in [0.0, 1.0]")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "target_ref": self.target_ref,
            "confidence_score": self.confidence_score,
            "uncertainty_score": self.uncertainty_score,
            "evidence_density_score": self.evidence_density_score,
            "agreement_score": self.agreement_score,
            "confidence_basis": [b.to_dict() for b in self.confidence_basis],
            "threshold_decision": self.threshold_decision.to_dict(),
            "explanation": self.explanation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfidenceAssessment":
        td_raw = data["threshold_decision"]
        td = ThresholdDecision(
            threshold_band=td_raw["threshold_band"],
            recommended_action=td_raw["recommended_action"],
            blocking=td_raw["blocking"],
        )
        basis = [
            ConfidenceBasis(
                basis_type=b["basis_type"],
                source_ref=b["source_ref"],
                contribution_weight=b["contribution_weight"],
                note=b.get("note"),
            )
            for b in data.get("confidence_basis", [])
        ]
        return cls(
            assessment_id=data["assessment_id"],
            target_ref=data["target_ref"],
            confidence_score=data["confidence_score"],
            uncertainty_score=data["uncertainty_score"],
            evidence_density_score=data["evidence_density_score"],
            threshold_decision=td,
            explanation=data.get("explanation", ""),
            confidence_basis=basis,
            agreement_score=data.get("agreement_score"),
        )


# ── Default threshold policy ──────────────────────────────────────────────

_DEFAULT_THRESHOLD_POLICY: List[tuple] = [
    # (min_confidence, band, action, blocking)
    (0.75, ThresholdBand.HIGH, RecommendedAction.CONTINUE, False),
    (0.50, ThresholdBand.MEDIUM, RecommendedAction.VERIFY_MORE, False),
    (0.25, ThresholdBand.LOW, RecommendedAction.VERIFY_MORE, False),
    (0.0, ThresholdBand.CRITICAL_LOW, RecommendedAction.HUMAN_REVIEW, True),
]


def classify_confidence(score: float) -> ThresholdDecision:
    """Classify a confidence score into a ThresholdDecision using default policy."""
    for min_score, band, action, blocking in _DEFAULT_THRESHOLD_POLICY:
        if score >= min_score:
            return ThresholdDecision(
                threshold_band=band,
                recommended_action=action,
                blocking=blocking,
            )
    return ThresholdDecision(
        threshold_band=ThresholdBand.CRITICAL_LOW,
        recommended_action=RecommendedAction.HUMAN_REVIEW,
        blocking=True,
    )


def build_assessment(
    *,
    target_ref: str,
    confidence_score: float,
    uncertainty_score: Optional[float] = None,
    evidence_density_score: float = 0.5,
    confidence_basis: Optional[List[ConfidenceBasis]] = None,
    agreement_score: Optional[float] = None,
    explanation: str = "",
    assessment_id: Optional[str] = None,
) -> ConfidenceAssessment:
    """Convenience factory: build an assessment from score inputs."""
    if uncertainty_score is None:
        uncertainty_score = max(0.0, 1.0 - confidence_score)
    td = classify_confidence(confidence_score)
    return ConfidenceAssessment(
        assessment_id=assessment_id or str(uuid.uuid4()),
        target_ref=target_ref,
        confidence_score=confidence_score,
        uncertainty_score=uncertainty_score,
        evidence_density_score=evidence_density_score,
        threshold_decision=td,
        explanation=explanation,
        confidence_basis=confidence_basis or [],
        agreement_score=agreement_score,
    )
