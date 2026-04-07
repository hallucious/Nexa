# CURRENT_STATE

Version: 1.0.0

---

## Purpose

This document is the current truth snapshot for the repository state at the latest verified UI/i18n convergence point.

It exists to reduce ambiguity about what is already implemented, what is only partially closed, and what should happen next.

This document is intentionally status-oriented.
It does not replace the canonical architecture or contract documents.

---

## Authoritative Snapshot

* authoritative implementation baseline commit: `d11e80c`
* authoritative verified baseline: `1806 passed, 9 skipped`
* status source: latest repository snapshot aligned to the post-workspace/hub UI i18n batch

---

## Current Position Summary

The current repository is no longer in a “UI not started” state.

The UI sector has already moved through:

* adapter / view-model foundation
* module-level view models for Core 5 and expanded slots
* UI-owned storage and commit-boundary rules
* multilingual UI foundation
* i18n persistence boundary verification
* panel-level and workspace / shell / hub-level localized display retrofit

The practical meaning is:

* engine-owned truth remains canonical
* UI-owned state remains bounded
* Working Save / Commit Snapshot / Execution Record separation is preserved
* multilingual UI is structurally present now, not postponed to a hypothetical later redesign

---

## Sector Status Matrix

| Sector | Status | Notes |
|---|---|---|
| execution engine core | Complete baseline | dependency-based runtime, savefile execution, provider/plugin runtime, observability foundations present |
| storage role split (`working_save` / `commit_snapshot`) | Complete baseline | role-aware `.nex` loading/validation/model split present |
| UI adapter / view-model layer | Complete baseline | adapter boundary and module view-models exist across panel/workspace/hub surfaces |
| UI persistence boundary | Complete baseline | `.nex.ui` and commit-boundary stripping rules implemented and test-backed |
| UI i18n foundation | Complete baseline | language resolution, fallback, localized message lookup, persistence boundary present |
| UI i18n retrofit (major surfaces) | Complete baseline | panel, workflow, workspace, shell, and hub display surfaces substantially localized |
| trace / artifact / storage / diff UI surfaces | Implemented view-model layer | underlying view-model contracts and Python-side projections exist; full end-user frontend shell is still a later integration layer |
| Designer proposal-flow UI surface | Implemented view-model layer | proposal / precheck / preview / approval projection exists at view-model level |
| Subcircuit support | Implemented foundation | loader, validator, runtime path, savefile roundtrip, and review-bundle example coverage exist |
| productized frontend shell | Not closed | replaceable UI shell architecture exists, but final end-user frontend product integration remains later work |

---

## What Is Closed Enough To Treat As Stable

### 1. UI sector foundation

The following should now be treated as stable enough not to reopen casually:

* UI sits above engine truth through the adapter / view-model boundary
* UI-owned state does not redefine structural truth, approval truth, execution truth, or storage lifecycle truth
* `.nex.ui` is UI continuity state, not approved canonical truth
* canonical Commit Snapshot must not carry canonical UI state
* app language / AI response language / format locale are separate concepts

### 2. Storage / UI boundary

The following should now be treated as closed baseline behavior:

* Working Save may carry UI-owned continuity state
* Commit Snapshot must strip canonical UI state
* snapshot-side `ui` must not be surfaced as canonical truth
* storage-role distinctions must remain visible in UI projections

### 3. Major i18n direction

The following are now baseline decisions, not open debate topics:

* Nexa UI must be structurally multilingual
* English + Korean is the initial supported language set
* i18n is not cosmetic-only; it is a UI architecture concern
* localized display must not leak into engine-owned truth

---

## Important Corrections To Earlier Mental Models

### 1. The project is not “about to start UI”

That model is incorrect.

The repository already contains substantial UI-sector code and tests under `src/ui/` and `tests/test_ui_*`.
The current stage is closer to:

* foundation implemented
* view-model surfaces broadly covered
* shell/product integration and documentation sync still remaining

### 2. The immediate bottleneck is not new UI theory

The bottleneck is now:

* keeping status/index documents aligned with code
* integrating the existing UI foundation into more product-shaped flows
* avoiding documentation drift that misrepresents actual completion state

---

## Recommended Next Work

### 1. Adapter / versioning / cross-reference sync

High priority.

The UI and i18n code has moved ahead of some top-level summary documents.
That drift should be kept small.

### 2. Product-flow integration across existing UI sectors

High priority.

The next practical integration problem is not another isolated view model.
It is connecting the already-built pieces into clearer end-user shell flows across:

* visual editing
* validation / approval
* storage lifecycle
* execution monitoring
* designer proposal review

### 3. Low-priority remaining text-surface cleanup

Medium priority.

Major UI surfaces are already localized, but small scattered fallback-backed text surfaces may still remain.
These should be cleaned in grouped passes rather than reopened one string at a time.

### 4. Full frontend shell/productization

Later priority.

The architecture explicitly supports a replaceable UI shell, but the repository is still stronger in engine/view-model foundations than in final end-user frontend packaging.

---

## Non-Goals For The Immediate Next Batch

The following are not the best immediate next step:

* inventing another large UI theory bundle
* reopening already-closed storage-role boundaries
* treating UI continuity as if it were approved truth
* broad architecture reshaping without status/doc sync first

---

## Short Next-Step Recommendation

The most rational immediate next batch after this status sync is:

**adapter/versioning + current-state documentation convergence, followed by product-flow integration work on top of the existing UI foundation.**
