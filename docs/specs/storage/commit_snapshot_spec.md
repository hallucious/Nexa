# Commit Snapshot Spec v0.1

## 1. Purpose

Commit Snapshot is the approval-gated structural snapshot artifact of Nexa.

It serves as:
- reproducible execution anchor
- stable comparison target
- rollback target
- audit/reference point

## 2. Core Principles

1. Commit Snapshot must represent approved structural state.
2. Commit Snapshot must not include unresolved blocking issues.
3. Commit Snapshot must be reproducible and structurally deterministic.
4. Commit Snapshot must not inherit temporary editor clutter.
5. Commit Snapshot is structure-oriented, not draft-oriented and not history-oriented.

## 3. Main Sections

```text
CommitSnapshot
- meta
- circuit
- resources
- state
- validation
- approval
- lineage
```

## 4. Responsibilities

Commit Snapshot stores:
- approved circuit structure
- approved resources
- approved baseline state
- approval summary
- validation summary
- commit lineage metadata

Commit Snapshot does NOT store:
- active editor/UI state
- pending designer ambiguity
- full run history
- full artifact payloads
- unapproved local draft clutter

## 5. Creation Rules

A Commit Snapshot may be created only if:
- proposal is not blocked
- required approval decision points are satisfied
- approved patch scope matches validated preview scope
  or changed scope has been revalidated
- no unresolved blocking findings remain
- snapshot contents are structurally deterministic

## 6. Boundary Rule

Working Save is editable present-state truth.
Commit Snapshot is approved structural truth.

They are related, but not interchangeable.

## 7. Decision

Commit Snapshot is the approval-gated structural anchor of Nexa.
It freezes approved structure for reproducibility, comparison, rollback, and later execution anchoring.
