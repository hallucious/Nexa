"""confidence_aggregator.py

Confidence propagation logic for the Uncertainty / Confidence Model.

Rules (per spec):
  - downstream confidence may not silently reset to high when upstream is low
  - strong verifier confirmation may partially recover confidence
  - absent evidence density limits upward confidence recovery
"""
from __future__ import annotations

from typing import List, Optional

from src.contracts.confidence_contract import (
    ConfidenceAssessment,
    ConfidenceBasis,
    BasisType,
    build_assessment,
)


class ConfidenceAggregatorError(ValueError):
    pass


def propagate_confidence(
    *,
    upstream_assessments: List[ConfidenceAssessment],
    local_evidence_density: float = 0.5,
    verifier_boost: float = 0.0,
    target_ref: str,
    explanation: str = "",
) -> ConfidenceAssessment:
    """Compute downstream confidence from upstream assessments.

    Rules:
      1. Min of upstream confidence scores is the propagation floor.
      2. Evidence density caps upward recovery.
      3. Verifier boost (0.0–0.2) may partially recover from a low-confidence upstream.
      4. Result confidence never exceeds upstream floor + recovery.
    """
    if not upstream_assessments:
        # No upstream: rely solely on local evidence density
        confidence = local_evidence_density
        return build_assessment(
            target_ref=target_ref,
            confidence_score=confidence,
            evidence_density_score=local_evidence_density,
            explanation=explanation or "no upstream dependencies; local evidence only",
        )

    upstream_floor = min(a.confidence_score for a in upstream_assessments)
    avg_evidence = sum(a.evidence_density_score for a in upstream_assessments) / len(
        upstream_assessments
    )
    combined_evidence = (avg_evidence + local_evidence_density) / 2.0

    # Verifier boost is capped at 0.2 and capped by evidence density ceiling
    capped_boost = min(verifier_boost, 0.2)
    evidence_ceiling = combined_evidence  # evidence density caps recovery

    raw_confidence = upstream_floor + capped_boost
    confidence = min(raw_confidence, evidence_ceiling, 1.0)
    confidence = max(confidence, 0.0)

    basis = [
        ConfidenceBasis(
            basis_type=BasisType.HISTORY,
            source_ref=a.target_ref,
            contribution_weight=round(1.0 / len(upstream_assessments), 4),
            note=f"upstream confidence={a.confidence_score:.3f}",
        )
        for a in upstream_assessments
    ]

    return build_assessment(
        target_ref=target_ref,
        confidence_score=round(confidence, 4),
        evidence_density_score=round(combined_evidence, 4),
        confidence_basis=basis,
        explanation=explanation
        or f"propagated from {len(upstream_assessments)} upstream(s); floor={upstream_floor:.3f}",
    )


def aggregate_parallel_confidence(
    assessments: List[ConfidenceAssessment],
    *,
    target_ref: str,
    strategy: str = "min",
) -> ConfidenceAssessment:
    """Aggregate confidence from parallel branches.

    strategy: 'min' (conservative), 'mean', 'max' (optimistic).
    Disagreement (high spread) lowers the result unless strategy='max'.
    """
    if not assessments:
        raise ConfidenceAggregatorError("assessments list must not be empty")

    scores = [a.confidence_score for a in assessments]
    spread = max(scores) - min(scores)

    if strategy == "min":
        base = min(scores)
    elif strategy == "mean":
        base = sum(scores) / len(scores)
    elif strategy == "max":
        base = max(scores)
    else:
        raise ConfidenceAggregatorError(f"unsupported strategy: {strategy!r}")

    # Disagreement penalty (spread > 0.3 gets a 10% penalty)
    penalty = 0.1 if spread > 0.3 else 0.0
    if strategy == "max":
        penalty = 0.0  # optimistic strategy ignores disagreement penalty

    confidence = max(0.0, base - penalty)
    avg_evidence = sum(a.evidence_density_score for a in assessments) / len(assessments)

    agreement_score = round(1.0 - spread, 4)

    return build_assessment(
        target_ref=target_ref,
        confidence_score=round(confidence, 4),
        evidence_density_score=round(avg_evidence, 4),
        agreement_score=agreement_score,
        explanation=(
            f"aggregated {len(assessments)} parallel candidates; "
            f"strategy={strategy}; spread={spread:.3f}"
        ),
    )
