# Trace Intelligence Spec v0.1

## Recommended save path
`docs/specs/precision/trace_intelligence_spec.md`

## 1. Purpose

This document defines the official Trace Intelligence layer for Nexa.

Its purpose is to upgrade trace from passive history into analyzable operational evidence.

This layer supports:
- structured node/resource rationale
- failure taxonomy
- replay mutation
- trace diff
- bottleneck analysis
- attribution of improvement and degradation

## 2. Core Decision

Trace must become an analysis surface, not just an audit log.

Official rule:

- trace remains engine-owned
- trace must be queryable and comparable
- trace intelligence may derive insights, but may not rewrite trace truth

## 3. Core Principles

1. trace is first-class
2. trace intelligence is derived from trace, not a replacement for it
3. live and historical trace remain distinct
4. replay and original trace remain distinct
5. derived summaries must preserve provenance
6. missing trace must remain visible as missing
7. trace intelligence must support later verifier and memory systems

## 4. Canonical Objects

TraceIntelligenceReport
- report_id: string
- run_ref: string
- trace_refs: list[string]
- failure_taxonomy: FailureTaxonomySummary
- bottleneck_summary: BottleneckSummary
- diff_summary: optional TraceDiffSummary
- replay_mutation_summary: optional ReplayMutationSummary
- attribution_summary: AttributionSummary
- explanation: string

FailureTaxonomySummary
- categories: list[FailureCategoryCount]
- top_reason_codes: list[string]
- repeated_failure_patterns: list[string]

BottleneckSummary
- slowest_nodes: list[string]
- highest_cost_nodes: list[string]
- highest_failure_rate_nodes: list[string]
- lowest_quality_contribution_nodes: list[string]

TraceDiffSummary
- source_run_ref
- target_run_ref
- changed_nodes
- changed_route_choices
- changed verifier outcomes
- changed artifacts
- changed final decision signals

ReplayMutationSummary
- replay_ref
- mutated_fields: list[string]
- expected_effect
- observed_effect
- consistency_note

AttributionSummary
- helpful_changes: list[string]
- harmful_changes: list[string]
- uncertain_changes: list[string]

## 5. Minimum Trace Enrichment

For trace intelligence to work, trace should retain:

- node/resource start and end
- reads/writes references
- verifier results
- route decisions
- confidence decisions
- artifact refs
- reason_codes
- retry / branch / merge signals

## 6. Replay Mutation Rules

Replay mutation means:
- replaying a run with one controlled change
- comparing outcomes against the original

Allowed mutation examples:
- prompt variant
- model route variant
- verifier policy variant
- threshold variant

Replay mutation must never overwrite original run truth.

## 7. Trace Diff Rules

Trace diff must support answering:
- why run A and run B diverged
- where verifier outcomes changed
- whether cost rose for useful reasons
- whether routing changes improved quality
- whether branch/merge behavior changed final outputs

## 8. First Implementation Scope

The first implementation should support:

- failure taxonomy summary
- bottleneck summary
- simple run-to-run trace diff
- replay mutation metadata
- attribution scaffold
- trace-linked explanations

## 9. Non-Goals for v0.1

Not required initially:

- universal causality proof
- automatic full-text natural language trace narration
- unrestricted causal graph synthesis
- speculative trace reconstruction when source data is missing

## 10. Final Decision

Trace Intelligence is the official explainability-and-improvement layer for Nexa trace.

It turns trace from:
"history that exists"

into:
"history that can teach the engine something"
