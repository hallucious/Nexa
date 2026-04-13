# CURRENT_STATE

Version: 1.3.0

---

## Purpose

This document is the current truth snapshot for the repository state at the latest verified convergence point.

It exists to reduce ambiguity about what is already implemented, what is only partially closed, and what should happen next.

This document is intentionally status-oriented.
It does not replace the canonical architecture or contract documents.

---

## Authoritative Snapshot

* authoritative implementation baseline commit: `12577dc`
* authoritative verified baseline: `2281 passed, 14 skipped`
* status source: latest repository snapshot aligned to the current handoff baseline (`Nexa_12577dc.zip`)
* canonical roadmap reference: `nexa_implementation_order_final_v2_2.md`

---

## Current Position Summary

The current repository should now be understood in two layers at once.

### 1. Canonical roadmap layer

The macro dependency order still comes from `nexa_implementation_order_final_v2_2.md`:

* beginner/productization priorities remain real
* Phase 4.5 still has its own macro gate and infrastructure-decision framing
* later phases such as accessibility/localization completion and product expansion still remain part of the long-term plan, while the Phase 7 return-use loop can now be treated as closed at this baseline

### 2. Practical code-state layer

The actual `12577dc` codebase now includes the earlier Phase 4.5 continuity foundation plus the practical closure of the Phase 7 return-use loop.

The source now already contains:

* server-side workspace continuity foundations
* onboarding continuity foundations
* run admission / list / status / result continuity foundations
* artifact / trace continuity foundations
* provider secret / health / probe / probe-history continuity foundations
* aggregate recent-activity / history-summary continuity foundations
* Phase 7 return-use surfaces: circuit library, beginner-facing result history, onboarding continuity alignment, and in-product feedback channel
* route surface / framework binding / FastAPI binding layers for the product/API surface
* database schema families and in-memory continuity stores supporting that server line

The practical meaning is:

* the repository is no longer mainly waiting for a first provider-probe-persistence seam
* the biggest immediate weakness was top-level documentation lag, not absence of server continuity code
* future planning must keep the roadmap layer and the practical code-state layer visible together

---

## Sector Status Matrix

| Sector | Status | Notes |
|---|---|---|
| execution engine core | Complete baseline | dependency-based runtime, savefile execution, provider/plugin runtime, observability foundations present |
| storage role split (`working_save` / `commit_snapshot`) | Complete baseline | role-aware `.nex` loading/validation/model split present |
| UI adapter / view-model layer | Complete baseline | adapter boundary and module view-models exist across panel/workspace/hub surfaces |
| UI persistence boundary | Complete baseline | `.nex.ui` and commit-boundary stripping rules are implemented |
| UI i18n foundation | Complete baseline | language resolution, fallback, localized message lookup, persistence boundary present |
| Designer proposal-flow UI surface | Implemented baseline | proposal / precheck / preview / approval projection exists |
| Subcircuit support | Implemented baseline | loader, validator, runtime path, savefile roundtrip, and official example coverage exist |
| Phase 4.5 database foundation | Implemented baseline | schema families for workspace registry, run history, onboarding state, managed provider bindings, provider probe events, artifact index, and trace event index are present |
| Phase 4.5 server continuity surfaces | Implemented baseline | workspace / onboarding / run / artifact-trace / provider operational / aggregate surfaces are already broad |
| continuity support stores | Implemented baseline | provider binding, managed secret metadata, provider probe history, workspace registry, and onboarding state stores exist |
| route / binding / FastAPI surface | Implemented baseline | HTTP route surface, framework binding, and FastAPI binding are already wired |
| general-user product shell | Not yet the dominant implementation truth | roadmap priority remains real, but current code has advanced further on server continuity than on beginner/product closure |
| remaining edge / exception continuity coverage | Not fully inventoried | likely residual low-frequency surfaces still need explicit mapping |

---

## What Is Closed Enough To Treat As Stable

### 1. The codebase is already beyond the old `d468795` status world

That older status line is now historical.
It must not continue to anchor top-level truth.

### 2. The server continuity family is real

The current repository already contains a broad server/product continuity layer.
Future work should treat that as existing baseline reality, not as a hypothetical design target.

### 3. The UI/storage/designer foundations remain valid

The older UI-sector convergence work is still real and implemented.
The newer server continuity line sits on top of that reality rather than replacing it.

### 4. Macro roadmap and practical code-state must stay separated conceptually

The roadmap still defines desired dependency order.
The code snapshot tells us what is already in source.
One must not erase the other.

---

## Important Corrections To Earlier Mental Models

### 1. The project is not currently “waiting to start Phase 4.5 server continuity”

That model is incorrect for `12577dc`.
The code is already materially inside that sector.

### 2. The immediate bottleneck was not missing server foundation code

The immediate bottleneck was that top-level truth documents still described an older world.

### 3. The next step is not “invent another adjacent continuity seam by habit”

The next step after this truth sync is to identify the real remaining gaps and choose one bounded next seam deliberately.

---

## What Still Remains Open

### 1. Remaining edge / exception / admin / collaboration continuity coverage

The current broad continuity family still needs an explicit remaining-gap inventory.
Some lower-frequency surfaces may remain outside the normalized projection family.

### 2. Route/binding/export integrity under future changes

Every new surface still risks drift across the route surface, framework binding, FastAPI binding, and package export layers.

### 3. General-user productization closure beyond Phase 7

Beginner shell enforcement and first-success blockers still remain part of the broader roadmap, but the Stage 3 return-use loop itself is now practically closed at this baseline. The next official open product work after this point is Phase 8 inclusion work (accessibility and localization completeness).

---

## Practical Interpretation

The project should now be interpreted as:

**engine/storage/UI foundations implemented, broad server/product continuity present in code, Phase 7 return-use loop practically closed at `12577dc`, and the next responsible move being to advance to Phase 8 inclusion work rather than extending Phase 7 indefinitely.**
