# State Branch / Merge Spec v0.1

## Recommended save path
`docs/specs/precision/state_branch_merge_spec.md`

## 1. Purpose

This document defines the official State Branch / Merge system for Nexa.

Its purpose is to allow bounded hypothesis exploration without breaking Nexa's runtime invariants.

This system supports:
- alternate candidate paths
- temporary state forks
- branch comparison
- controlled merge decisions

## 2. Core Decision

Nexa may support branching, but branching must remain explicit, bounded, and merge-governed.

Official rule:

- branches are not hidden retries
- branches create explicit branch states
- merges require a declared merge policy
- unresolved branch conflicts must remain visible

## 3. Position in Architecture

Base State
→ branch creation
→ branch execution set
→ comparison
→ merge / discard / escalate

Branching extends execution.
It does not replace Node-only execution.

## 4. Core Principles

1. branch creation is explicit
2. branch scope is bounded
3. branch identity is stable
4. merge policy is mandatory
5. branch comparisons are structured
6. discarded branches remain traceable
7. parent truth and branch truth must not silently collapse

## 5. Canonical State Objects

BranchStateRef
- branch_id: string
- parent_state_ref: string
- branch_reason: string
- branch_policy: string
- created_at: string

BranchCandidate
- branch_id
- produced_state_ref
- quality_summary
- cost_summary
- confidence_summary
- verifier_summary
- merge_eligibility

MergeDecision
- merge_id: string
- merge_policy: enum("best_score", "majority_vote", "human_select", "rule_based")
- selected_branch_id: optional string
- selected_state_ref: optional string
- discarded_branch_ids: list[string]
- conflict_report: ConflictReport
- explanation: string

ConflictReport
- has_conflict: bool
- conflicting_keys: list[string]
- conflict_type: enum("structural", "artifact", "confidence", "policy", "unknown")
- requires_human_review: bool

## 6. Branch Policies

Initial supported branch policies:

- alternative_generation
- alternative_repair
- alternative_routing
- low_confidence_split
- verifier_disagreement_split

Each branch policy must justify why branching occurred.

## 7. Merge Rules

Merge must never be silent when branch outputs materially disagree.

Required merge inputs:
- quality comparison
- verifier result comparison
- cost comparison
- confidence comparison
- policy safety comparison

Policy safety veto dominates merge convenience.

## 8. Boundedness Rules

Every branch set must be bounded by policy.

Minimum controls:
- max_branch_count
- max_branch_depth
- max_merge_wait
- max_branch_budget
- forced_human_review thresholds

## 9. Trace Rules

Branching must preserve:

- branch creation reason
- branch execution history
- branch verifier outcomes
- merge decision
- discarded branch references

This is required for:
- replay
- analysis
- future memory reuse
- bias detection

## 10. First Implementation Scope

The first implementation should support:

- explicit branch objects
- bounded branch creation
- branch comparison summary
- single merge decision object
- best-score merge policy
- human-select merge policy
- branch trace persistence

## 11. Non-Goals for v0.1

Not required initially:

- unlimited search-tree execution
- automatic global reasoning graph synthesis
- hidden Monte Carlo style branch explosion
- self-modifying merge policy

## 12. Final Decision

The State Branch / Merge system is the official bounded exploration extension for Nexa.

It allows alternative reasoning paths while preserving:
- explicit state ownership
- merge accountability
- traceability
- cost control
