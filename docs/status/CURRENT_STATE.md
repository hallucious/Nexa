# CURRENT_STATE

Version: 1.5.0

---

## Purpose

This document is the current truth snapshot for the repository state at the latest verified convergence point.

It exists to reduce ambiguity about what is already implemented, what is only partially closed, and what should happen next.

This document is intentionally status-oriented.
It does not replace the canonical architecture or contract documents.

---

## Authoritative Snapshot

* latest confirmed repository baseline: `e6ee133`
* latest verified baseline: `2321 passed, 14 skipped`
* status source: latest repository snapshot aligned to the current handoff baseline (`Nexa_e6ee133.zip`)
* canonical macro roadmap reference: `nexa_implementation_order_final_v2_2.md`
* canonical productization reference: `docs/specs/ui/general_user_productization_priority.md`
* practical next-seam rule: treat Phase 7 and Phase 8 as closed enough to stop being the default work mode, and keep the next official line inside Phase 9 public-boundary / integration consolidation

---

## Current Position Summary

The current repository should now be understood in three practical layers at once.

### 1. Architecture / engine layer

The engine, storage, UI adapter, designer, runtime, and observability foundations remain the stable implementation base.

### 2. Product continuity layer

The codebase already contains the broad Phase 4.5 server/product continuity foundation plus the practical closure of the Phase 7 return-use loop:

* server-backed circuit library
* beginner-facing result history
* onboarding continuity alignment
* in-product feedback channel

### 3. Inclusion / product-completeness layer

The current surfaced beginner / return-use product path has now also practically closed Phase 8:

* accessibility implementation is materially present on the surfaced shell / library / result / feedback path
* Korean localization completeness is materially present on the current beginner / return-use surfaced path
* remaining visible English is predominantly fixture data, payload values, or internal identifiers rather than critical surfaced product copy debt

---

## Sector Status Matrix

| Sector | Status | Notes |
|---|---|---|
| execution engine core | Complete baseline | dependency-based runtime, savefile execution, provider/plugin runtime, observability foundations present |
| storage role split (`working_save` / `commit_snapshot`) | Complete baseline | role-aware `.nex` loading/validation/model split present |
| UI adapter / view-model layer | Complete baseline | adapter boundary and module view-models exist across panel/workspace/hub surfaces |
| UI persistence boundary | Complete baseline | `.nex.ui` and commit-boundary stripping rules are implemented |
| UI i18n foundation | Complete baseline | language resolution, fallback, localized lookup, EN/KO surfaced-path completeness present |
| Designer proposal-flow UI surface | Implemented baseline | proposal / precheck / preview / approval projection exists |
| Subcircuit support | Implemented baseline | loader, validator, runtime path, savefile roundtrip, and official example coverage exist |
| Phase 4.5 database foundation | Implemented baseline | schema families and continuity stores remain present |
| Phase 4.5 server continuity surfaces | Implemented baseline | workspace / onboarding / run / artifact-trace / provider operational / aggregate surfaces are broad |
| Phase 7 return-use loop | Complete baseline | circuit library, beginner result history, onboarding continuity alignment, and in-product feedback are closure-audited |
| Phase 8 inclusion / product completeness | Complete baseline | surfaced accessibility and Korean localization closure are now practical and closure-audited |
| surfaced metadata / terminology refinement | Complete baseline | major user-facing metadata and terminology cleanup batches have been applied |
| Phase 9 (Stage 5 product expansion) | In progress | public-boundary-first expansion is now active; `src.sdk` and `src.sdk.integration` establish the public spine and minimal MCP adapter/export scaffolding has started the Phase 9.2 integration line |

---

## What Is Closed Enough To Treat As Stable

### 1. The old `12577dc` / `2281 passed, 14 skipped` status world is no longer current top-level truth

That older world remains historically important because it closed Phase 7.
It is no longer the best top-level truth snapshot for current planning.

### 2. The server continuity family is real and stable baseline reality

Future planning should treat the broad server/product continuity line as existing code, not as speculative design.

### 3. Phase 7 is closed enough to keep closed

Return-use loop work should not be reopened casually unless a concrete contradiction is found in source or tests.

### 4. Phase 8 is now also closed enough to keep closed

The surfaced beginner / return-use accessibility and Korean localization line is now implemented strongly enough that it should not remain open by habit.

---

## What Still Remains Open

### 1. Phase 9 (Stage 5 product expansion)

The next official product-facing line is Phase 9.

Its first seam should be public-boundary-first expansion work such as:

* public `.nex` format standardization
* SDK / public API boundary clarification
* public-contract versus internal-implementation boundary declaration

Later Phase 9 layers may then cover:

* MCP / integration-surface work
* circuit sharing
* community / ecosystem expansion

`user accounts / sessions` must not be reintroduced here as a fresh Phase 9 line; that continuity foundation already belongs to Phase 4.5 in the canonical roadmap.

### 2. Non-blocking wording / polish debt outside the surfaced path

Some older or less central surfaces may still contain technical wording or non-ideal copy.
That is no longer a Phase 8 blocker at this baseline.

### 3. Route / binding / export integrity under future changes

Every new surfaced family still risks drift across:

* `src/server/http_route_surface.py`
* `src/server/framework_binding.py`
* `src/server/fastapi_binding.py`
* `src/server/__init__.py`

---

## Practical Interpretation

The project should now be interpreted as:

**engine/storage/UI foundations are implemented, broad server/product continuity is present in code, Phase 7 and Phase 8 are closed strongly enough to keep closed, and the current responsible top-level move is to continue Phase 9 public-boundary / integration work from the verified `e6ee133` / `2321 passed, 14 skipped` baseline rather than reopening older seams.**
