# Working Save Spec v0.1

## 1. Purpose

Working Save is the editable, always-saveable storage artifact of Nexa.

It preserves current working state, including:
- incomplete circuit drafts
- invalid drafts
- validation-failed drafts
- Designer-generated but unapproved proposals
- editor-facing state

## 2. Core Principles

1. Working Save must always be saveable.
2. Working Save may be incomplete or invalid.
3. Working Save preserves user work even when execution is impossible.
4. Working Save must remain lightweight.
5. Working Save is current-state oriented, not approval-oriented, and not history-oriented.

## 3. Main Sections

```text
WorkingSave
- meta
- circuit
- resources
- state
- runtime
- ui
- designer? (optional)
```

## 4. Responsibilities

Working Save stores:
- current circuit draft
- current editable resources
- current editable state
- current validation summary
- current error summary
- latest execution summary (optional)
- editor/UI state
- local design metadata

Working Save does NOT store:
- full approval history
- full patch lineage history
- full execution trace history
- large artifact payload archives

## 5. Always-Saveable Rule

A Working Save must remain writable even when:
- entry is missing
- final output is missing
- provider config is unresolved
- plugin config is unresolved
- validation failed
- execution failed
- approval is pending

## 6. Runtime Meaning

`runtime.status` describes current working condition, not approval truth.

Typical values:
- draft
- validation_failed
- ready_for_review
- validated
- execution_failed
- executed

## 7. Decision

Working Save is the always-saveable present-state artifact of Nexa.
It preserves editable current reality, even when incomplete, invalid, or unapproved.
