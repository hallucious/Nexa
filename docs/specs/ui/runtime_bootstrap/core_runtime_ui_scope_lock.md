# Core Runtime UI Scope Lock

## Recommended save path
`docs/specs/ui/runtime_bootstrap/core_runtime_ui_scope_lock.md`

## 1. Purpose

This document fixes the immediate implementation boundary for the Nexa runtime shell.

Its purpose is to stop scope drift and to make one thing explicit:

**the next UI work is not generic UI theory expansion.  
The next UI work is runtime-shell closure around the minimum product-driving shell surface.**

This document defines:
- what is in the immediate runtime closure scope
- what is out
- what each in-scope module is responsible for
- what “done” means at this stage

## 2. Core Decision

The immediate runtime shell closure set is:

1. Shell
2. Graph Workspace
3. Inspector
4. Validation
5. Execution
6. Storage

This is the only correct “now” scope for core product-driving UI closure.

Historical UI architecture still distinguishes core slots and extended slots,
but the practical closure set must include Storage because:

- Save / Review / Commit / Run meaning must remain legible
- Working Save / Commit Snapshot / Execution Record boundary must remain visible
- end-user flow breaks if storage role visibility is weak

## 3. Why These 6 Are In

### 3.1 Shell
The whole runtime surface needs one stable composition root.
Without shell closure, every panel remains locally correct but globally fragmented.

### 3.2 Graph Workspace
Graph remains the navigation anchor and primary visual model of the system.
Without graph closure there is no coherent structural workspace.

### 3.3 Inspector
Selection without bounded detail reading/edit-intent input is incomplete.
Inspector is the official selected-object detail surface.

### 3.4 Validation
Validation is not a later collaboration feature.
It is the runtime safety and readiness surface for:
- blocked findings
- warning findings
- confirmation-required risk
- why run or commit cannot proceed

### 3.5 Execution
Execution is the official runtime-state and progress surface.
Without it the shell cannot be considered product-driving.

### 3.6 Storage
Storage is not optional at this phase.
It is the only surface that keeps:
- Working Save
- Commit Snapshot
- Execution Record
legible to the user during real product flow.

## 4. What Is Explicitly Out of Scope for This Closure Step

The following are not part of immediate runtime-shell closure:

- collaboration
- shared review view
- comments / annotations / review thread system
- review issue lifecycle
- reviewer authority / approval record system
- multi-user review orchestration

These may remain documented, but they must not become blockers for current shell closure.

## 5. In-Scope Responsibilities by Module

### 5.1 Shell
- compose runtime-facing modules
- preserve role/mode/global status visibility
- keep action routing coherent
- host command palette / top-level navigation
- coordinate primary focus surfaces

### 5.2 Graph Workspace
- render current structure
- render previewable structural deltas when relevant
- reflect active / blocked / failed / selected states
- remain the navigation anchor

### 5.3 Inspector
- display selected-object detail
- collect bounded edit intent
- show read-only vs editable distinctions
- expose related validation / execution context

### 5.4 Validation
- show overall readiness
- surface blocking / warning / confirmation-required findings
- map findings to graph or selected object
- explain why a run or commit is not allowed

### 5.5 Execution
- show current run state
- show progress and current active node
- show latest outputs and run events
- expose bounded run controls when allowed

### 5.6 Storage
- show current storage role
- show Working Save ↔ Commit Snapshot ↔ Execution Record relationship
- show uncommitted-change state
- show run anchoring / snapshot anchoring
- expose bounded storage actions when allowed

## 6. Hard Constraints

1. UI remains a shell above engine truth.
2. No module may redefine structural / validation / execution / storage truth.
3. `.nex.ui` remains Working Save-only canonical UI continuity.
4. Commit Snapshot must not become a carrier for editor continuity.
5. Validation remains in-scope even though collaboration is out-of-scope.
6. Storage remains in-scope even if historical “core slot” language treated it as extended.

## 7. Definition of Done for Scope Lock

The scope lock is considered successful only when:

- all active implementation planning references the same 6-module closure set
- no current plan treats collaboration specs as a runtime-shell blocker
- no current plan omits Storage from immediate closure
- no current plan relegates Validation to “later review work”

## 8. Final Statement

At this phase, the correct Nexa UI runtime closure boundary is:

**Shell + Graph + Inspector + Validation + Execution + Storage**

Everything else is either observability expansion or later review-system work.