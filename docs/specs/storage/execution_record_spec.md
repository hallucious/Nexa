# Execution Record Spec v0.1

## 1. Purpose

Execution Record is the run-scoped historical execution artifact of Nexa.

It preserves the result and history of one concrete execution of a circuit based on a specific Commit Snapshot.

It exists to support:
- replay
- audit
- debugging
- comparison
- observability
- result inspection

## 2. Core Principles

1. One Execution Record corresponds to exactly one run.
2. It must reference the Commit Snapshot used for execution.
3. It preserves execution history, not editable draft truth.
4. It may contain detailed trace and artifact references.
5. It is append-only after run completion, except clearly defined later indexing / annotation if allowed.
6. Stronger explicit or materializable execution truth must outrank weaker stale derived metadata during normalization.

## 3. Main Sections

```text
ExecutionRecord
- meta
- source
- input
- timeline
- node_results
- outputs
- artifacts
- diagnostics
- observability
```

## 4. Responsibilities

Execution Record stores:
- run identity
- commit reference
- input summary / reference
- trace summary / reference
- node-level outcomes
- artifact references
- runtime metrics
- warnings / errors / failure summary
- final outputs
- timing metadata

It does NOT store:
- editable current draft state
- UI / editor transient state
- approval decision flow
- unapproved designer ambiguity state

## 5. Truth-Ordering Rule

If execution metadata disagrees during materialization or normalization:
- sufficiently substantive native execution record wins first
- richer materializable execution truth wins next
- thin identity-only execution data may survive only where identity must be preserved
- stale replay payload fields, stale derived contracts, and weak wrapper metadata must not override stronger truth

## 6. Rule

Execution Record must always reference one `commit_id`.
It is an execution-history artifact, not a replacement for Working Save or Commit Snapshot.

## 7. Decision

Execution Record is the run-scoped historical artifact of Nexa.
It captures what actually happened during one execution of one approved structural snapshot.

## 8. Precision Projection Addendum (v0.2)
Execution Record is the canonical projection surface for runtime-visible precision metadata.
When precision data exists in runtime trace, execution record MAY project:

- route summaries
- safety summaries
- confidence summaries
- node-level precision summaries
- human decision summaries derived from runtime review-gate decision events
- trace-intelligence summaries derived from node-level trace evidence
- branch summaries derived from bounded branch-candidate declaration events


These are observability and audit surfaces.
They MUST NOT redefine structural truth, approval truth, or baseline gating semantics.

