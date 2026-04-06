# Uncertainty / Confidence Model Spec v0.1

## Recommended save path
`docs/specs/precision/uncertainty_confidence_model_spec.md`

## 1. Purpose

This document defines the official Uncertainty / Confidence Model for Nexa.

Its purpose is to standardize how Nexa represents:

- confidence
- uncertainty
- evidence density
- agreement / disagreement
- confidence propagation
- threshold-driven escalation

This prevents outputs from being treated as fully trustworthy merely because they exist.

## 2. Core Decision

Nexa must represent uncertainty explicitly.

Official rule:

- confidence is not implied by fluent output
- low-confidence outputs remain usable but must be marked
- uncertainty may affect routing, branching, verification, and escalation

## 3. Core Principles

1. confidence is structured
2. uncertainty is visible
3. confidence must cite its basis
4. confidence propagation must be explicit
5. disagreement lowers confidence unless justified
6. confidence thresholds may trigger action
7. confidence must not be fabricated by UI

## 4. Canonical Result Object

ConfidenceAssessment
- assessment_id: string
- target_ref: string
- confidence_score: float
- uncertainty_score: float
- evidence_density_score: float
- agreement_score: optional float
- confidence_basis: list[ConfidenceBasis]
- threshold_decision: ThresholdDecision
- explanation: string

ConfidenceBasis
- basis_type: enum("evidence", "verifier", "agreement", "history", "heuristic")
- source_ref: string
- contribution_weight: float
- note: optional string

ThresholdDecision
- threshold_band: enum("high", "medium", "low", "critical_low")
- recommended_action: enum("continue", "verify_more", "branch", "reroute", "human_review", "stop")
- blocking: bool

## 5. Propagation Rules

When a downstream output depends on low-confidence upstream outputs:

- confidence may not silently reset to high
- downstream confidence must incorporate upstream uncertainty
- strong verifier confirmation may partially recover confidence
- absent evidence density limits upward confidence recovery

## 6. Disagreement Rules

Disagreement may come from:

- multiple providers
- multiple branches
- verifier conflict
- evidence inconsistency

Disagreement must remain visible.
Consensus without explanation is not enough.

## 7. Evidence Density

Evidence density is a separate measure from confidence.

It estimates:
- amount of support
- diversity of support
- directness of support
- freshness / relevance when applicable

Low evidence density may cap maximum confidence.

## 8. Threshold Actions

Initial threshold actions:

- high → continue
- medium → continue or verify more
- low → verify more or branch
- critical_low → human review or stop

Threshold policy must remain configurable.

## 9. First Implementation Scope

The first implementation should support:

- confidence score
- uncertainty score
- evidence density score
- threshold band
- recommended action
- propagation from a single upstream dependency set
- trace linkage

## 10. Non-Goals for v0.1

Not required initially:

- mathematically perfect Bayesian confidence
- universal truth probability
- hidden confidence smoothing
- automatic self-certification by the producer alone

## 11. Final Decision

The Uncertainty / Confidence Model is the official anti-false-certainty layer for the precision track.

It forces Nexa to say:
"this is the output, and this is how sure we are"

instead of:
"this output exists, therefore treat it as reliable"
