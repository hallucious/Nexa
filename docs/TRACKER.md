# Nexa TRACKER

Version: 3.1.0

---

## Purpose

This document is the planning-and-status tracker for the current uploaded repository baseline.

It exists to answer five practical questions:

1. What roadmap still governs the project?
2. What code reality is actually present right now?
3. What sectors are already implemented enough to stop misdescribing them?
4. What remains genuinely open?
5. What should happen next without reopening stale mental models?

This tracker is intentionally implementation-aware.
It does not replace BLUEPRINT or the detailed spec set.

---

## Roadmap Authority

The canonical macro implementation order remains:

- `nexa_implementation_order_final_v2_2.md`

That roadmap still governs long-range sequencing.

However, the practical code reality in the uploaded repository is already deep into a broad **Phase 4.5 server/product continuity** line.
That means two truths must be held together:

1. the macro roadmap still governs long-range sequencing
2. the current repository already contains a large server/API continuity surface that must be described honestly

This tracker therefore distinguishes:

- **macro roadmap authority**
- **practical current code state**

They are related, but they are not identical.

---

## Authoritative Baseline

* authoritative implementation baseline commit: `d468795`
* latest explicitly confirmed verified baseline: `2087 passed, 13 skipped`
* latest verified repo archive used for this tracker: `Nexa_d468795.zip`

---

## Current Repository Reality

The current repository is best described as:

**engine/storage/designer/UI foundations substantially implemented, with a broad server/product continuity layer already present above the engine core.**

This is no longer accurately described by the older `c869806` / `1848 passed, 9 skipped` shell-convergence-only picture.

---

## Implemented Surface Summary

### 1. Core execution engine

Implemented baseline includes:

* dependency-based circuit runtime
* node execution phases (pre / core / post)
* ExecutionConfig registry, hashing, validation, and loading
* savefile-based `.nex` execution
* observability and runtime metrics foundations
* execution event stream foundations
* graph-only runtime execution centered on node execution

### 2. Prompt / provider / plugin runtime

Implemented baseline includes:

* prompt registry integration in runtime paths
* provider execution through the provider runtime boundary
* plugin auto-loading / registry-aligned execution
* result canonicalization in the runtime path
* bounded compatibility handling for legacy execution surfaces

### 3. Storage / savefile lifecycle

Implemented baseline includes:

* role-aware `.nex` storage with `working_save` and `commit_snapshot`
* Execution Record treated as run-history rather than a savefile role
* canonical save/load/validate lifecycle APIs
* subcircuit-preserving roundtrip support
* storage semantics owned by storage/lifecycle APIs rather than ad hoc CLI-local interpretation

### 4. Designer / UI foundation

Implemented baseline includes:

* UI adapter / view-model boundary
* Core 5 and expanded UI module surfaces
* `.nex.ui` Working Save continuity boundary and commit-boundary stripping rules
* English/Korean UI localization foundation
* substantial builder/workflow/shell/workspace/product-flow projection surfaces
* Designer session-state / proposal / precheck / preview / approval foundations

### 5. Server / product continuity layer

This is the most important currently underdescribed implemented surface.

The uploaded repository already contains a broad `src/server/` line including:

* workspace continuity APIs and stores
* onboarding continuity APIs and stores
* run admission / run list / run read APIs
* artifact / trace read APIs
* recent activity aggregation
* provider binding / secret / health / probe / probe-history APIs
* worker queue orchestration models
* framework binding / FastAPI binding / HTTP route surface layers
* database foundation and migration foundation
* AWS Secrets Manager binding models

Representative continuity stores already present:

* `workspace_registry_store.py`
* `onboarding_state_store.py`
* `provider_binding_store.py`
* `managed_secret_metadata_store.py`
* `provider_probe_history_store.py`

### 6. Current repository shape signals

Directly inspectable from the uploaded archive:

* `src/server/`: 43 top-level files
* `tests/test_server_*.py`: 22 files
* major source sectors present simultaneously:
  * `engine`
  * `storage`
  * `designer`
  * `ui`
  * `server`
  * `providers`
  * `contracts`
  * `platform`

---

## What Must No Longer Be Misdescribed

The following older descriptions are now inaccurate and should not be reused:

### 1. “UI is not started yet”
Incorrect.
The repository already contains a substantial UI-sector codebase.

### 2. “The project is still mainly in late product-flow shell proof work”
Incomplete.
That shell/product-flow line exists, but the uploaded codebase has already expanded materially into server continuity infrastructure.

### 3. “Phase 4.5 is only a future design topic”
Incorrect.
The codebase already contains broad pre-product server continuity implementation under the Phase 4.5 theme.

### 4. “The top-level truth docs are already synchronized by default”
Incorrect until this sync batch.
The earlier status layer was behind the repository reality and required explicit correction.

---

## Stable Enough To Stop Reopening

The following should now be treated as stable baseline decisions unless real contradictory code evidence appears:

### 1. Engine truth ownership

* engine owns structural truth
* engine owns approval truth
* engine owns execution truth
* UI may project and coordinate, but must not redefine those truths

### 2. UI continuity boundary

* `WorkingSaveModel.ui` is allowed
* canonical snapshot-side `ui` is not allowed
* Working Save -> Commit Snapshot must strip or reject canonical `ui`

### 3. Designer governance direction

* Designer remains proposal-first
* Designer must not silently mutate committed truth
* approval/revision continuity remains explicit rather than implicit

### 4. Server continuity existence

The broad server/API continuity surface is already real code, not just planning language.
Future work may refine or consolidate it, but it should not be described as absent.

### 5. Roadmap authority distinction

The macro roadmap still comes from `nexa_implementation_order_final_v2_2.md` even though current code reality is already deep in the Phase 4.5 server line.

---

## Must Remain Open

The following are still genuinely open and should not be falsely marked complete:

### 1. Formal Phase 4.5 implementation-gate closure

The repository contains broad server continuity implementation,
but the architecture/gate question is still real:

* hosting decision
* database decision
* authentication decision
* secret/provider credential decision
* server API shape decision
* mobile/web session continuity decision

These decisions exist as documents under `docs/specs/meta/phase45_decisions/`,
and production-grade expansion should not pretend the gate question is already trivial.

### 2. Route / binding / export parity audit

Because the repository now has:

* HTTP route surface
* framework bindings
* FastAPI bindings
* per-surface models

there is a real risk of drift between route definitions, bindings, and exported behavior.
That audit remains open.

### 3. Final product-facing frontend realization

The Python-side UI shell and projection layers are substantial,
but they are not yet the same thing as a finished end-user frontend product.

### 4. Macro-roadmap reconciliation

The project still needs an explicit decision about whether the next major implementation push should:

* continue Phase 4.5 consolidation
or
* return to roadmap-sequenced beginner / first-success / productization work

That reconciliation is still open.

---

## Immediate Next Priority

Now that the top-level truth docs are synchronized to `d468795`, the most rational next batch is:

**Phase 4.5 consolidation before another broad expansion batch.**

Practical meaning:

1. audit route / binding / model parity across `http_route_surface`, `framework_binding`, and `fastapi_binding`
2. audit server stores/schema families/tests against the Phase 4.5 decision set
3. decide whether the current server line is still pre-gate prototype/convergence work or whether the gate is now formally satisfied
4. only then choose whether to continue deeper server implementation or pivot back to the roadmap’s beginner/productization-first line

---

## Working Interpretation For The Next Session

Use the following interpretation by default:

* the codebase is ahead of the older top-level status docs
* the repository is already materially inside a server/product continuity build-out
* docs must not drift back to the older `c869806` worldview
* new implementation should not begin from a false “UI not started / server not built” assumption
* the next work should be chosen from a truthful `d468795` baseline, not from stale status language
