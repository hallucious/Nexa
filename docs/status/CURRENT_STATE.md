# CURRENT_STATE

Version: 1.1.0

---

## Purpose

This document is the current truth snapshot for the repository state at the latest verified convergence point.

It exists to reduce ambiguity about what is already implemented, what is only partially closed, and what should happen next.

This document is intentionally status-oriented.
It does not replace the canonical architecture or contract documents.

---

## Authoritative Snapshot

* authoritative implementation baseline commit: `c869806`
* authoritative verified baseline: `1848 passed, 9 skipped`
* status source: latest repository snapshot aligned to the post-E2E-proof product-flow shell baseline

---

## Current Position Summary

The current repository is no longer in a “UI not started” state.

The UI / storage / designer line has already moved through:

* adapter / view-model foundation
* module-level view models for Core 5 and expanded slots
* UI-owned storage and commit-boundary rules
* multilingual UI foundation
* i18n persistence boundary verification
* panel-level and workspace / shell / hub-level localized display retrofit
* product-flow shell convergence across journey / runbook / handoff / readiness / E2E path / closure / transition / gateway / E2E proof

The practical meaning is:

* engine-owned truth remains canonical
* UI-owned state remains bounded
* Working Save / Commit Snapshot / Execution Record separation is preserved
* multilingual UI is structurally present now, not postponed to a hypothetical later redesign
* product-flow shell work is now in late convergence rather than early construction

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
| trace / artifact / storage / diff shell surface | Implemented shell-linked baseline | underlying view-model contracts and shell-linked Python-side projections exist |
| Designer proposal-flow UI surface | Implemented shell-linked baseline | proposal / precheck / preview / approval projection exists and is shell-linked |
| Subcircuit support | Implemented foundation | loader, validator, runtime path, savefile roundtrip, and review-bundle example coverage exist |
| productized frontend shell | Not fully closed | replaceable UI shell architecture exists and late convergence is substantial, but final end-user frontend productization remains later work |
| live E2E user-flow proof | Not fully closed | the product-flow shell can now describe and gate the path, but final live commit/run/follow-through proof still remains |

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

### 4. Product-flow shell convergence baseline

The following are now part of the current implemented baseline:

* product-flow shell composition exists
* journey / runbook / handoff / readiness / E2E path / closure / transition / gateway projections exist
* the remaining gap is no longer “should these shell layers exist,” but “is the final live boundary behavior fully closed?”

---

## Important Corrections To Earlier Mental Models

### 1. The project is not “about to start UI”

That model is incorrect.

The repository already contains substantial UI-sector code and tests under `src/ui/` and `tests/test_ui_*`.
The current stage is closer to:

* foundation implemented
* shell/product-flow convergence substantially implemented
* broader frontend realization and general-user productization still remaining

### 2. The immediate bottleneck is not new UI theory

The bottleneck is now:

* keeping top-level documents synchronized with actual code reality
* finishing final live boundary proof where needed
* avoiding drift between high-level status language and the implemented shell/product-flow state

---

## What Still Remains Open

The following items are still open and should not be overclaimed.

### 1. Final live E2E verification
The shell can now describe the user-flow path and its gates, but real workflow proof across commit/run/follow-through remains the last serious technical gap.

### 2. Final Designer control-plane convergence
Designer proposal/gating surfaces are present, but final proof of the whole review/approval/revision path still needs to be treated as live workflow work, not merely projection work.

### 3. Finished frontend product shell
The Python-side shell/product-flow control plane is strong enough to guide further implementation, but it is not yet the same thing as a finished end-user frontend application.

---

## Practical Interpretation

The project should now be interpreted as:

**engine/storage/UI foundations implemented, shell/product-flow convergence broadly present through E2E proof, and documentation synchronized to that reality.**
