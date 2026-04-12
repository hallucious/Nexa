# CURRENT_IMPLEMENTATION_STATE

Version: 1.2.0

## Purpose

This document is the short-form implementation truth sheet for the current uploaded repository baseline.

It exists to answer four practical questions quickly:

1. What is already implemented in code?
2. What is only partially converged?
3. What should not be reopened casually?
4. What is still genuinely open after the repository moved into a broad server/product continuity line?

This document is intentionally implementation-first.
It is not a replacement for BLUEPRINT or the detailed spec documents.

## Authoritative Snapshot

- authoritative implementation baseline commit: `d468795`
- latest explicitly confirmed verified baseline: `2087 passed, 13 skipped`
- status source: uploaded `Nexa_d468795.zip` plus the matching session handoff baseline

## One-Line Position

Nexa is **not** in a “UI not started” state,
and it is also no longer accurately described as only a late shell/product-flow convergence repository.

It is in an **engine/storage/designer/UI foundation complete enough, broad Phase 4.5 server/product continuity already present** state.

## Sector Matrix

| Sector | Status | Practical meaning |
|---|---|---|
| execution engine core | Complete baseline | dependency-based runtime, savefile execution, provider/plugin runtime, and observability foundations are present |
| storage / savefile lifecycle | Complete baseline | role-aware `.nex` lifecycle and savefile/state semantics are present |
| UI adapter / view-model layer | Complete baseline | Core UI projections exist across panel/workspace/shell surfaces |
| UI persistence / storage boundary | Complete baseline | Working Save may carry UI continuity; Commit Snapshot must not carry canonical `ui` |
| UI i18n foundation | Complete baseline | EN fallback plus KO/EN UI resource support and persistence boundary are present |
| Designer proposal/control foundation | Implemented baseline | session-state / proposal / precheck / preview / approval surfaces are code-backed |
| shell / workflow / product-flow projection | Implemented baseline | builder/workflow/shell/workspace/product-flow hubs and projections are present |
| server continuity/API layer | Broad implemented surface | workspace/onboarding/run/provider/artifact-trace/activity continuity APIs and stores already exist |
| framework/FastAPI route binding layer | Implemented but audit-sensitive | HTTP route surface, framework bindings, and FastAPI bindings are present and now require parity discipline |
| database/migration foundation | Implemented baseline | schema-family modeling and migration foundation exist for server continuity sectors |
| productized frontend shell | Not fully closed | Python-side UI shell/projections are substantial, but this is not yet a finished end-user frontend product |
| formal Phase 4.5 gate closure | Not fully closed | the code surface exists, but production-grade gate decisions still require explicit closure |

## Stable Enough To Stop Reopening

The following should now be treated as closed baseline decisions unless a real contradiction is found.

### 1. Engine/UI truth ownership
- engine owns structural truth
- engine owns approval truth
- engine owns execution truth
- UI may project and coordinate, but must not redefine those truths

### 2. UI continuity boundary
- `WorkingSaveModel.ui` is allowed
- canonical snapshot-side `ui` is not allowed
- Working Save -> Commit Snapshot must strip or reject canonical `ui`

### 3. Designer governance direction
- Designer remains proposal-first
- Designer may not silently mutate committed truth
- explicit approval/revision continuity remains required

### 4. Server continuity existence
- the `src/server/` continuity layer is already real code and tests
- future work may refine it, but it should not be described as missing

### 5. Macro-roadmap distinction
- the canonical macro roadmap still comes from `nexa_implementation_order_final_v2_2.md`
- current code reality being deep in Phase 4.5 does not erase that roadmap authority

## Must Remain Open

The following are still open and should not be falsely marked complete.

### 1. Formal Phase 4.5 implementation-gate closure
The decision set exists, but production-grade closure still depends on explicit confirmation of hosting/auth/database/secret/API/session choices.

### 2. Route / binding / export parity
The current server line has enough surface area that drift between route definitions, framework bindings, and FastAPI bindings is now a real implementation risk.

### 3. Broader end-user frontend productization
The Python-side UI shell and workflow/product-flow projections are substantial, but they are not yet the same thing as a finished user-facing frontend product.

### 4. Macro-roadmap reconciliation
The project still needs an explicit choice about whether the next large push continues deeper server continuity or returns to roadmap-sequenced beginner/productization work.

## Reopen-Prohibited Topics

Do not casually reopen the following:

- whether UI is above the engine
- whether `.nex.ui` may become canonical snapshot truth
- whether Designer may silently mutate committed truth
- whether the server continuity/API line already exists in the repository
- whether the macro roadmap still matters once current code reality moved into Phase 4.5

## Keep-Open Topics

Continue treating the following as active implementation topics:

- formal Phase 4.5 implementation-gate closure
- route / binding / export parity across the server surface
- server continuity consolidation
- broader frontend/product realization beyond the Python-side shell
- roadmap reconciliation after truthful top-level status synchronization

## Recommended Immediate Next Batch

The most rational immediate next batch is:

**consolidate the existing Phase 4.5 server continuity line before adding another broad implementation family.**

Practical meaning:

1. audit `http_route_surface`, `framework_binding`, and `fastapi_binding` for parity
2. audit server stores/schema families/tests against the Phase 4.5 decision documents
3. decide whether the current server line is still pre-gate convergence work or whether the gate is now formally satisfied
4. only then choose whether to continue deeper server implementation or pivot back to roadmap-sequenced beginner/productization work
