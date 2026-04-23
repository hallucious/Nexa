# Core Runtime UI Implementation Plan

## Recommended save path
`docs/specs/ui/runtime_bootstrap/core_runtime_ui_implementation_plan.md`

## 1. Purpose

This document defines the implementation plan for closing the immediate Nexa runtime shell.

It is intentionally not a fresh greenfield UI plan.
It assumes UI foundation already exists and that current work must converge existing modules into a coherent product-driving shell.

## 2. Implementation Premise

Already-existing UI foundation means this plan must prefer:
- integration over reinvention
- extension over rewrite
- linkage over speculative redesign
- regression-aware convergence over broad new theory work

## 3. Immediate Closure Modules

The runtime closure set is fixed:

1. Shell
2. Graph Workspace
3. Inspector
4. Validation
5. Execution
6. Storage

## 4. Phase Breakdown

### Phase 1 — Shell Composition Stabilization

Goal:
establish one reliable runtime composition root.

Tasks:
- stabilize builder shell composition
- ensure top bar / global status / action cluster / navigation entry points remain coherent
- ensure role, mode, and global readiness remain always visible
- normalize cross-panel routing

Outputs:
- one reliable runtime shell composition path
- one consistent main entry surface
- shell-level state coordination that does not own truth

### Phase 2 — Graph ↔ Inspector Closure

Goal:
close the primary structure-reading and detail-reading loop.

Tasks:
- stabilize graph selection model
- ensure graph selection consistently drives inspector
- ensure inspector edit requests remain intent-based
- ensure selected object context remains stable across build/review/run emphasis shifts

Outputs:
- reliable select → inspect → emit intent loop
- no direct raw mutation path from inspector
- no ambiguity about selected target

### Phase 3 — Validation Integration Closure

Goal:
make readiness and blocking state impossible to miss.

Tasks:
- stabilize overall readiness summary
- ensure blocking/warning/confirmation-required findings remain visible
- ensure finding → graph/object jump works
- ensure validation state is reflected in top-level actions and summaries

Outputs:
- user can always see whether current target is pass / warning / blocked
- user can always see why a run or commit is not allowed
- validation no longer behaves like an isolated panel

### Phase 4 — Execution Integration Closure

Goal:
make run-state legible and operational from the shell.

Tasks:
- stabilize execution status model
- reflect current run state in shell-level status and graph highlights
- ensure latest outputs and recent events are visible
- keep run controls bounded and role-aware

Outputs:
- user can always tell whether target is idle / queued / running / completed / failed
- execution feels like part of the shell, not a detached panel
- run-state and structure context remain linked

### Phase 5 — Storage Integration Closure

Goal:
make storage-role meaning explicit and non-optional in daily use.

Tasks:
- stabilize storage role badge and storage panel linkage
- show Working Save / Commit Snapshot / Execution Record relationship
- surface uncommitted-change state
- surface snapshot/run anchoring state
- ensure save/review/commit/run action meanings stay legible

Outputs:
- user no longer confuses Save with Commit
- storage role remains visible and meaningful
- storage panel becomes part of runtime shell closure, not later optional expansion

### Phase 6 — Cross-Module User-Flow Closure

Goal:
close the end-user path across all six modules.

Tasks:
- verify new workspace flow
- verify edit flow
- verify blocked validation flow
- verify run flow
- verify storage transition flow
- verify return-to-graph and cross-panel recovery paths

Outputs:
- one coherent user-flow path across the runtime shell
- no dead-end transitions between modules
- shell-level flow works for beginner-visible core actions

## 5. What This Plan Explicitly Avoids

This implementation plan does not:
- reopen truth boundary debates
- reclassify collaboration specs as current blockers
- defer Storage to later
- treat Validation as optional
- rewrite already-implemented modules from scratch unless required by verified mismatch

## 6. Regression Expectations

Every phase above must preserve:
- engine-owned truth boundary
- adapter/view-model access discipline
- `.nex.ui` Working Save-only rule
- no Commit Snapshot UI carry-over
- no fake execution history projection

## 7. Completion Criteria

This implementation plan is complete only when:

- shell-level runtime closure works across the 6-module set
- storage role is always legible
- validation status is always legible
- execution status is always legible
- graph remains the anchor
- end-to-end runtime flow is regression-tested

## 8. Final Statement

The current UI plan is not:
“design a UI.”

It is:
**converge the existing UI foundation into a product-driving runtime shell.**