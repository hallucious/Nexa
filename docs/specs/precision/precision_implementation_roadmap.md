# Precision Implementation Roadmap v0.1

## Recommended save path
`docs/specs/precision/precision_implementation_roadmap.md`

## 1. Purpose

This document defines the implementation order for the precision-improvement track after the documentation bundle is approved.

Its purpose is to avoid random feature implementation and to preserve dependency order.

## 2. Fixed Dependency Order

Official order:

### Batch 1 — Quality Core
1. Evaluation / Verifier Layer
2. Typed Artifact Contract

Reason:
These two establish the minimum quality boundary.

### Batch 2 — Explainability Core
3. Trace Intelligence
4. Uncertainty / Confidence Model

Reason:
Once quality exists, Nexa must explain and qualify it.

### Batch 3 — Controlled Generation
5. Designer AI Constraint System
6. Policy / Safety Gate

Reason:
Proposal generation and safe execution boundaries must be constrained before autonomy grows.

### Batch 4 — Exploration Core
7. State Branch / Merge
8. Budget-Aware Routing

Reason:
Exploration and routing should be added only after quality, explanation, and safety are stable.

### Batch 5 — Governance and Learning
9. Human-in-the-Loop Decision Nodes
10. Outcome Learning Memory

Reason:
Governance and historical learning are most valuable after upstream layers emit stable structured outputs.

## 3. First Coding Targets

Recommended first coding targets:

1. `VerifierResult` model
2. reason_code registry
3. artifact type registry
4. typed artifact envelope
5. trace enrichment fields for verifier and typed artifact linkage
6. confidence assessment envelope
7. minimal designer constraint policy model

## 4. Minimum Test Plan

The precision track should begin with tests for:

- malformed output detection
- missing required artifact type detection
- verifier aggregation correctness
- reason_code stability
- confidence threshold actions
- trace linkage persistence
- designer lint blocking for forbidden patterns

## 5. Completion Criteria for Documentation Phase

The documentation phase is complete when:

- all bundle documents exist
- paths are fixed
- implementation order is fixed
- overlaps with existing docs are clarified
- first coding targets are identified

## 6. Completion Criteria for First Implementation Phase

The first implementation phase is complete when:

- verifier results are structured
- typed artifacts are validated
- trace records verifier and artifact linkage
- confidence can trigger verify-more or human-review actions
- basic designer constraints can block invalid proposals

## 7. Final Decision

The precision track must be implemented as a dependency-ordered system, not as an unstructured feature list.

This roadmap is the official sequence for that work.
