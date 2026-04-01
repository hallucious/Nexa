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
5. It is append-only after run completion, except clearly defined later indexing/annotation if allowed.

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
- input summary/reference
- trace summary/reference
- node-level outcomes
- artifact references
- runtime metrics
- warnings/errors/failure summary
- final outputs
- timing metadata

It does NOT store:
- editable current draft state
- UI/editor transient state
- approval decision flow
- unapproved designer ambiguity state

## 5. Rule

Execution Record must always reference one `commit_id`.
It is an execution-history artifact, not a replacement for Working Save or Commit Snapshot.

## 6. Decision

Execution Record is the run-scoped historical artifact of Nexa.
It captures what actually happened during one execution of one approved structural snapshot.
