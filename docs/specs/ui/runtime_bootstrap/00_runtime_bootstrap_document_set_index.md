# Runtime Bootstrap Document Set Index

## Recommended save path
`docs/specs/ui/runtime_bootstrap/00_runtime_bootstrap_document_set_index.md`

## Purpose

This index defines the canonical document set for the next UI phase of Nexa.

The current priority is not to continue deepening the review/collaboration system first.
The current priority is to turn the existing UI foundation into a real runtime-capable shell that can:

- open a working draft
- render the graph
- inspect selected objects
- surface validation
- request execution
- show execution state
- show storage role and lifecycle boundaries

After that, the next expansion is runtime observability.
Only after that should the deferred review/collaboration system be re-entered.

This document set therefore formalizes four linked documents:

1. Core Runtime UI Scope Lock
2. Core Runtime UI Implementation Plan
3. Runtime Observability UI Expansion Plan
4. Review System Reentry Plan

## Why this set exists

Nexa already has meaningful UI foundation work in place.
The current risk is not “lack of UI concepts”.
The current risk is drift:

- continuing to produce more abstract UI contracts without closing the runtime shell
- mixing review-system depth with runtime-shell priorities
- allowing UI work to blur engine-owned truth boundaries
- implementing screens without a locked scope and completion definition

This set exists to stop that drift.

## Authority order

These documents should be read in this order:

1. `01_core_runtime_ui_scope_lock.md`
2. `02_core_runtime_ui_implementation_plan.md`
3. `03_runtime_observability_ui_expansion_plan.md`
4. `04_review_system_reentry_plan.md`

Interpretation rule:

- Scope Lock decides what counts as the current product target
- Implementation Plan decides how to build that target
- Observability Expansion decides what comes immediately after shell closure
- Review Reentry decides when and how deferred review features come back

## Canonical storage folder

All documents in this set should be stored under:

`docs/specs/ui/runtime_bootstrap/`

## Canonical document list

### 1. Core Runtime UI Scope Lock
Path:

`docs/specs/ui/runtime_bootstrap/01_core_runtime_ui_scope_lock.md`

Role:
- fixes the current implementation target
- declares the six-module runtime shell
- separates included vs excluded scope
- prevents review-system drift

### 2. Core Runtime UI Implementation Plan
Path:

`docs/specs/ui/runtime_bootstrap/02_core_runtime_ui_implementation_plan.md`

Role:
- defines the implementation sequence
- defines build order
- defines integration order
- defines test and completion checkpoints

### 3. Runtime Observability UI Expansion Plan
Path:

`docs/specs/ui/runtime_bootstrap/03_runtime_observability_ui_expansion_plan.md`

Role:
- defines the first expansion after the six-module shell closes
- integrates Trace / Timeline / Artifact / Diff surfaces
- turns the shell into a real control-plane experience

### 4. Review System Reentry Plan
Path:

`docs/specs/ui/runtime_bootstrap/04_review_system_reentry_plan.md`

Role:
- defines the reentry conditions for collaboration/review work
- protects the runtime-shell-first priority
- prevents premature return to approval/governance depth

## Core cross-document invariants

All documents in this set must preserve the following invariants.

### 1. UI remains above the engine
Nexa UI is a shell above engine-owned truth.
It must not redefine structural truth, approval truth, execution truth, or storage truth.

### 2. The runtime shell must close before review-system depth returns
The next major UI milestone is a usable runtime shell, not a richer collaboration layer.

### 3. Validation is part of the runtime shell
Validation is not deferred review work.
Validation is part of the core operational UI because it explains blocked and warning states before commit or execution.

### 4. Storage role boundaries remain explicit
Working Save, Commit Snapshot, and Execution Record must remain visibly distinct.
The shell must not flatten them.

### 5. Intent/action boundaries remain explicit
The shell may emit intents and actions.
It may not directly mutate engine-owned truth.

## Final rule

This document set must be treated as a connected package.
It exists to move Nexa from “UI foundation exists” to “runtime shell is real and usable”, while keeping observability next and deep review later.
