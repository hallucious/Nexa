# Storage Architecture Overview v0.1

## 1. Purpose

This document defines the official three-layer storage architecture of Nexa.

The storage system must preserve:
- editable present state
- approved structural state
- historical execution state

without collapsing them into one ambiguous artifact.

## 2. Official Storage Layers

### 2.1 Working Save
- editable
- always-saveable
- may be incomplete
- may be invalid
- currentness-oriented

### 2.2 Commit Snapshot
- approval-gated
- structurally approved
- reproducible execution anchor
- rollback / diff baseline

### 2.3 Execution Record
- run-scoped
- history-oriented
- references one Commit Snapshot
- preserves what actually happened during one execution

## 3. Canonical Truth Ownership

The storage sector owns canonical storage semantics.
CLI, export, replay, and audit surfaces are consumers of storage/lifecycle semantics rather than independent owners of those semantics.

This means path-local reinterpretation of execution truth is considered a storage-sector bug.
Canonicalization and truth-ordering must converge through storage/lifecycle APIs.

## 4. Why Single Savefile Is Not Enough

A single save artifact tends to mix:
- draft state
- approved structure
- execution history

This causes lifecycle ambiguity and weakens replay / audit boundaries.

## 5. Lifecycle Boundary

```text
Working Save
-> Commit Snapshot
-> Execution Record
-> Updated Working Save summary
```

Meaning:
- save preserves current editable reality
- commit freezes approved structure
- execution creates historical run evidence
- working-save runtime may retain only lightweight latest-run summary, not full history

## 6. Concrete Format Mapping Summary

- `.nex` with `storage_role=working_save` -> Working Save
- `.nex` with `storage_role=commit_snapshot` -> Commit Snapshot
- execution record / trace / artifact refs -> Execution Record layer
- `.nexb` -> distribution bundle, not a lifecycle layer

## 7. Current Hardening Rule

When multiple representations disagree, stronger explicit or materializable execution truth must outrank weaker stale derived metadata.
This applies across helper, lifecycle, serialization, replay, export, and CLI-adjacent boundaries.

## 8. Design Rule

Save, commit, and execute are different boundaries and must remain different in schema, validation, lifecycle services, and truth-ordering behavior.
