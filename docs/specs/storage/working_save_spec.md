# Working Save Spec v0.1

## 1. Purpose

Working Save is the editable, always-saveable storage artifact of Nexa.

It preserves:
- incomplete drafts
- invalid drafts
- validation-failed drafts
- designer-generated but unapproved proposals
- editor-facing present state

## 2. Core Principles

1. Working Save must always be saveable.
2. It may be incomplete or invalid.
3. It preserves user work even when execution is impossible.
4. It must remain lightweight enough for routine editing and inspection.
5. It must not accumulate full historical trace or full artifact payload history.
6. It is currentness-oriented, not approval-oriented and not history-oriented.

## 3. Main Sections

```text
WorkingSave
- meta
- circuit
- resources
- state
- runtime
- ui
- designer (optional)
```

## 4. Responsibilities

Working Save stores:
- current circuit draft
- current editable resources
- current editable state
- current validation summary
- current error summary
- latest execution summary (optional)
- editor / UI state
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

`runtime.last_run` may keep lightweight execution summary, but it must not become a surrogate Execution Record.

## 7. Boundary Rule

Working Save may summarize execution, but it must not redefine structural truth or absorb full run history.
Approved structural truth lives in Commit Snapshot.
Historical run truth lives in Execution Record.

## 8. Decision

Working Save is the always-saveable present-state artifact of Nexa.
It preserves editable current reality, even when incomplete, invalid, or unapproved.
