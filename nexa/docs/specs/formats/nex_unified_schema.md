# `.nex` Unified Schema v0.1

## 1. Purpose

This document defines the unified top-level `.nex` schema shared by:
- `working_save`
- `commit_snapshot`

The `.nex` family is retained, but internal lifecycle meaning is split by `meta.storage_role`.

## 2. Common Top-Level Backbone

```text
.nex
- meta
- circuit
- resources
- state
```

These sections are shared structurally.

## 3. Role-Specific Branching Sections

### Working Save
Required:
- meta
- circuit
- resources
- state
- runtime
- ui

Optional:
- designer

Forbidden as durable truth:
- approval
- lineage
- commit validation truth section

### Commit Snapshot
Required:
- meta
- circuit
- resources
- state
- validation
- approval
- lineage

Forbidden:
- runtime (working-condition section)
- ui
- designer
- full run history
- artifact payload accumulation

## 4. `meta` Rule

```text
meta:
  format_version
  storage_role: working_save | commit_snapshot
  ...
```

Role-specific identity:
- `working_save_id` for Working Save
- `commit_id` for Commit Snapshot

## 5. Meaning of Shared Sections

The same top-level section may have different lifecycle semantics depending on parent role.
Example:
- `state` in Working Save = editable current state
- `state` in Commit Snapshot = approved baseline state

## 6. Current Direction

The role-aware `.nex` family is current architecture, not future-only groundwork.
Execution Record remains outside the `.nex` role split as the run-history layer.

## 7. Decision

`.nex` uses a common backbone plus explicit role-based branch sections.
