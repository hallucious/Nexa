# CURRENT_IMPLEMENTATION_STATE

Version: 1.1.0

## Purpose

This document is the short-form implementation truth sheet for the current repository state.

It exists to answer four practical questions quickly:

1. What is already implemented in code?
2. What is only partially converged?
3. What should not be reopened casually?
4. What is still genuinely open after the recent product-flow shell convergence work?

This document is intentionally implementation-first.
It is not a replacement for the detailed architecture/spec documents.

## Authoritative Snapshot

- authoritative implementation baseline commit: `f143396`
- authoritative verified baseline: `1844 passed, 9 skipped`
- status source: latest repository snapshot after product-flow gateway projection and top-level documentation synchronization

## One-Line Position

Nexa is **not** in a "UI not started" state.
It is in a **runtime/storage foundation complete, UI foundation implemented, product-flow shell largely converged, final live E2E proof still open** state.

## Sector Matrix

| Sector | Status | Practical meaning |
|---|---|---|
| UI adapter / view-model layer | Complete baseline | Core UI projections exist and are test-backed across panel/workspace/hub surfaces |
| UI persistence / storage boundary | Complete baseline | Working Save may carry UI continuity; Commit Snapshot must not carry canonical `ui` |
| i18n foundation | Complete baseline | translation lookup, EN fallback, KO/EN resources, UI language persistence boundary all exist |
| i18n major retrofit | Complete baseline | main panel / workflow / workspace / shell / hub surfaces are localized; residual cleanup is minor rather than architectural |
| live execution / trace / artifact / diff shell surface | Implemented shell-linked baseline | Python-side projections exist and are linked into product-flow shell composition |
| Designer proposal flow projection | Implemented shell-linked baseline | intent / patch / precheck / preview / approval data is projected into UI surfaces |
| product-flow shell integration | Implemented convergence baseline | shell/workspace/hub composition plus journey / runbook / handoff / readiness / E2E path / closure / transition / gateway projections are present |
| Subcircuit | Implemented foundation | schema/model/validator/runtime/example coverage exists; broader future work should be code-first, not theory-first |
| E2E user flow closure | Mostly converged | scenario-level shell/gateway projections now exist, but final live commit/run/follow-through proof is still an open engineering task |

## Stable Enough To Stop Reopening

The following should now be treated as closed baseline decisions unless a real contradiction is found.

### 1. UI truth ownership
- engine owns structural truth
- engine owns approval truth
- engine owns execution truth
- UI may project and coordinate, but must not redefine those truths

### 2. UI continuity boundary
- `WorkingSaveModel.ui` is allowed
- canonical snapshot-side `ui` is not allowed
- Working Save -> Commit Snapshot must strip or reject canonical `ui`

### 3. i18n direction
- Nexa UI is structurally multilingual now
- English fallback is mandatory
- Korean and English are the initial supported UI languages
- localized display must not leak into engine-owned truth

### 4. Shell architecture
- UI remains a replaceable shell above the engine
- adapter/view-model boundary remains mandatory
- panel/workspace/hub composition must not bypass the adapter boundary

### 5. Product-flow shell projection stack
- journey / runbook / handoff / readiness / E2E path / closure / transition / gateway are now part of the implemented shell-level convergence baseline
- future work should tighten real boundary behavior rather than reopen whether these projection families should exist

## Must Remain Open

The following are still open and should not be falsely marked complete.

### 1. Final live commit/run/follow-through proof
The shell now projects the relevant gates and boundaries, but live boundary proof still needs final convergence against real workflow behavior.

### 2. Final integrated Designer control-plane proof
The proposal-flow surfaces and gates exist, but end-to-end review/approval/revision behavior still needs final proof at the workflow boundary level.

### 3. Broader end-user frontend productization
The Python-side UI shell and product-flow control-plane models are substantially implemented, but they are not yet the same thing as a finished user-facing frontend product.

## Reopen-Prohibited Topics

Do not casually reopen the following:

- whether UI is above the engine
- whether `.nex.ui` may become canonical snapshot truth
- whether UI i18n should be postponed until later
- whether Designer may silently mutate committed truth
- whether storage-role visibility matters in the shell
- whether product-flow shell convergence should be replaced by another theory-only document cycle

## Keep-Open Topics

Continue treating the following as active implementation topics:

- final live E2E workflow proof
- real commit/run/follow-through convergence
- final Designer control-plane closure
- broader frontend/product shell realization beyond Python-side projection models

## Recommended Immediate Next Batch

The most rational immediate next batch is:

**perform one last technical convergence pass only if a real live E2E gap is found; otherwise treat top-level documentation as synchronized and move toward the next product-facing implementation line.**
