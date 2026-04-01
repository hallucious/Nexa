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
- rollback/diff baseline

### 2.3 Execution Record
- run-scoped
- history-oriented
- references one Commit Snapshot
- preserves what actually happened during one execution

## 3. Why Single Savefile Is Not Enough

A single save artifact tends to mix:
- draft state
- approved structure
- execution history

This causes lifecycle ambiguity and weakens replay/audit boundaries.

## 4. Lifecycle Boundary

```text
Working Save
-> Commit Snapshot
-> Execution Record
```

Meaning:
- save preserves current editable reality
- commit freezes approved structure
- execution creates historical run evidence

## 5. Concrete Format Mapping Summary

- `.nex` with `storage_role=working_save` -> Working Save
- `.nex` with `storage_role=commit_snapshot` -> Commit Snapshot
- execution record / trace / artifact refs -> Execution Record layer
- `.nexb` -> distribution bundle, not a lifecycle layer

## 6. Design Rule

Save, commit, and execute are different boundaries and must remain different in schema, validation, and lifecycle services.
