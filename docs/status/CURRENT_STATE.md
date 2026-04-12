# CURRENT_STATE

Version: 1.2.0

---

## Purpose

This document is the current truth snapshot for the repository state at the latest synchronized convergence point.

It exists to reduce ambiguity about:

* what is already implemented
* what is only partially closed
* what mental models are now outdated
* what should happen next from the truthful `d468795` baseline

This document is intentionally status-oriented.
It does not replace BLUEPRINT, TRACKER, or the canonical spec set.

---

## Authoritative Snapshot

* authoritative implementation baseline commit: `d468795`
* latest explicitly confirmed verified baseline: `2087 passed, 13 skipped`
* status source: uploaded `Nexa_d468795.zip` plus the matching handoff baseline

---

## Current Position Summary

The current repository is no longer accurately described by the older `c869806` shell/product-flow-only status picture.

The uploaded codebase now combines three large realities at once:

1. **engine / storage foundation** is already substantial
2. **Designer / UI shell foundation** is already substantial
3. **server/product continuity infrastructure** is already substantial

The practical meaning is:

* engine-owned truth remains canonical
* UI-owned state remains bounded
* Working Save / Commit Snapshot / Execution Record separation remains preserved
* Designer remains proposal-first rather than mutation-first
* the repository already contains a broad server/API continuity surface above the engine core

---

## Sector Status Matrix

| Sector | Status | Notes |
|---|---|---|
| execution engine core | Complete baseline | dependency-based runtime, provider/plugin execution, observability foundations present |
| storage role split (`working_save` / `commit_snapshot`) | Complete baseline | role-aware `.nex` loading/validation/model split present |
| Designer / UI foundation | Complete baseline | adapter boundary, panel/workspace/shell projections, and bounded proposal/control surfaces exist |
| UI persistence boundary | Complete baseline | `.nex.ui` Working Save continuity plus commit-boundary stripping are reflected in code/tests |
| UI i18n foundation | Complete baseline | EN fallback, KO/EN resources, and persistence boundary are present |
| server continuity/API layer | Broad implemented surface | workspace, onboarding, run, artifact/trace, provider, activity, queue, and binding layers are already present |
| server persistence foundation | Implemented baseline | database/schema/migration foundations plus continuity stores exist |
| route/binding stack | Implemented but audit-sensitive | HTTP route surface, framework bindings, and FastAPI bindings all exist and require parity discipline |
| productized frontend shell | Not fully closed | Python-side shell/projection layers are strong, but they are not yet a finished end-user frontend application |
| formal Phase 4.5 production gate | Not fully closed | production-grade expansion still depends on explicit gate closure across infra decisions |

---

## Important Corrections To Earlier Mental Models

### 1. The project is not “about to start UI”

That model is incorrect.
The repository already contains substantial UI-sector code under `src/ui/`.

### 2. The project is not only in a late shell-proof cycle anymore

That model is also incomplete.
The repository already contains a broad server/product continuity implementation under `src/server/`.

### 3. Phase 4.5 is not merely a future design topic

That model is incorrect.
The codebase already contains significant Phase 4.5-style continuity infrastructure and API surface.

### 4. The macro roadmap was not replaced by current code reality

That model is also incorrect.
The canonical macro roadmap still comes from `nexa_implementation_order_final_v2_2.md`.
Current code reality being deep in Phase 4.5 does not erase roadmap authority.

---

## What Is Closed Enough To Treat As Stable

### 1. Engine/UI truth ownership

The following should be treated as stable enough not to reopen casually:

* UI sits above engine truth through the adapter/view-model boundary
* UI-owned state does not redefine structural truth, approval truth, execution truth, or storage lifecycle truth
* `.nex.ui` is UI continuity state, not approved canonical truth
* canonical Commit Snapshot must not carry canonical UI state

### 2. Designer governance direction

The following should now be treated as stable baseline behavior:

* Designer is proposal-first
* Designer must not silently mutate committed truth
* approval/revision continuity remains explicit rather than implicit

### 3. Server continuity existence

The following is now part of the stable repository truth:

* workspace continuity APIs/stores exist
* onboarding continuity APIs/stores exist
* run admission/list/read APIs exist
* artifact/trace read APIs exist
* provider binding/secret/health/probe/probe-history APIs exist
* framework/FastAPI binding layers exist
* database/migration foundations exist

---

## What Still Remains Open

The following items are still open and should not be overclaimed.

### 1. Formal Phase 4.5 implementation-gate closure
The architecture decision set exists, but production-grade closure still depends on explicit confirmation of infra decisions.

### 2. Route / binding / export parity
The expanded server surface now makes parity drift a real risk that still needs explicit auditing.

### 3. Finished frontend product shell
The Python-side UI shell/product-flow control plane is strong enough to guide further implementation, but it is not yet a finished end-user frontend application.

### 4. Next major implementation direction
The project still needs an explicit choice about whether the next major push continues deeper server continuity or returns to roadmap-sequenced beginner/productization work.

---

## Practical Interpretation

The project should now be interpreted as:

**engine/storage/designer/UI foundations substantially implemented, broad server/product continuity already implemented, and top-level truth documents now synchronized to that `d468795` reality.**
