# CURRENT_IMPLEMENTATION_STATE

Version: 1.0.0

## Purpose

This document is the short-form implementation truth sheet for the current repository state.

It exists to answer four practical questions quickly:

1. What is already implemented in code?
2. What is only partially converged?
3. What should not be reopened casually?
4. What must remain open until product-flow integration is truly closed?

This document is intentionally implementation-first.
It is not a replacement for the detailed architecture/spec documents.

## Authoritative Snapshot

- authoritative implementation baseline commit: `8f111dd`
- authoritative verified baseline: `1806 passed, 9 skipped`
- status source: latest repository snapshot after top-level current-state sync and before product-flow shell integration closure

## One-Line Position

Nexa is **not** in a "UI not started" state.
It is in a **UI foundation implemented, shell/product integration still open** state.

## Sector Matrix

| Sector | Status | Practical meaning |
|---|---|---|
| UI adapter / view-model layer | Complete baseline | Core UI projections exist and are test-backed across panel/workspace/hub surfaces |
| UI persistence / storage boundary | Complete baseline | Working Save may carry UI continuity; Commit Snapshot must not carry canonical `ui` |
| i18n foundation | Complete baseline | translation lookup, EN fallback, KO/EN resources, UI language persistence boundary all exist |
| i18n major retrofit | Mostly complete | main panel / workflow / workspace / shell / hub surfaces are localized; small scattered surfaces may remain |
| live execution / trace / artifact / diff view-model surface | Implemented view-model layer | Python-side projections exist; end-user shell/product flow still needs stronger integration |
| Designer proposal flow projection | Implemented view-model layer | intent / patch / precheck / preview / approval data is projected into UI surfaces |
| product-flow shell integration | Partial | shell/workspace/hub composition exists, but top-level product-flow closure is still in progress |
| Subcircuit | Implemented foundation | schema/model/validator/runtime/example coverage exists; broader convergence should now be code-first |
| E2E user flow closure | Not closed | cross-surface story exists in pieces, but not yet locked as a full user workflow contract + regression set |

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

## Must Remain Open

The following are still open and should not be falsely marked complete.

### 1. Product-flow shell closure
The pieces exist, but they are not yet fully closed into the most direct end-user build/review/run workflow.

### 2. Execution observability integration at shell level
Trace, artifact, diff, execution, and storage surfaces exist, but they still need stronger shell-level linking and final UX closure.

### 3. Full Designer proposal control-plane closure
The proposal-flow surfaces exist, but full review/approval/revision interaction closure still requires integrated user-flow proof.

### 4. Full E2E user scenario regression
The repository still needs more user-journey-oriented tests rather than only module-by-module coverage.

## Reopen-Prohibited Topics

Do not casually reopen the following:

- whether UI is above the engine
- whether `.nex.ui` may become canonical snapshot truth
- whether UI i18n should be postponed until later
- whether Designer may silently mutate committed truth
- whether storage-role visibility matters in the shell

## Keep-Open Topics

Continue treating the following as active implementation topics:

- shell-level product-flow integration
- execution/trace/artifact/diff linkage inside the shell
- Designer review/approval loop closure
- final small-surface i18n cleanup
- E2E user-scenario regression closure

## Recommended Immediate Next Batch

The most rational immediate next batch is:

**continue shell/product-flow integration on top of the existing UI foundation, rather than producing another theory-only document bundle.**

Concretely, this means prioritizing:

1. shell-level workspace composition and top-level actions
2. command/quick-jump integration
3. execution/trace/artifact/diff linkage through shell-level navigation
4. Designer review/approval actions at shell level
5. user-flow-oriented regression tests
