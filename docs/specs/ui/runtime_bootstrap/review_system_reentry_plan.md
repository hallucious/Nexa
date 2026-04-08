# Review System Reentry Plan

## Recommended save path
`docs/specs/ui/runtime_bootstrap/review_system_reentry_plan.md`

## 1. Purpose

This document defines when and how review-system UI work should reenter after runtime-shell and observability closure.

Its purpose is to prevent collaboration/review design from prematurely hijacking current runtime-shell work.

## 2. Core Decision

Review-system UI is not cancelled.
It is sequenced later.

The correct order is:

1. core runtime shell closure
2. observability linkage closure
3. review-system reentry

## 3. Review-System Surface Set

Review-system reentry covers the following documented surfaces:

- collaboration / shared review view
- comments / annotations / review threads
- review resolution / issue lifecycle
- approval decision record / reviewer authority

These remain valid design documents.
They are simply not immediate blockers for current runtime closure.

## 4. Why Reentry Is Later

Because current product-driving value depends first on:
- coherent structure workspace
- readiness visibility
- execution visibility
- storage-role legibility
- observability linkage

Without those, multi-user review surfaces would be layered onto an unstable operational shell.

## 5. Reentry Preconditions

Review-system UI should reenter only after all of the following are true:

1. runtime shell closure across Shell + Graph + Inspector + Validation + Execution + Storage is stable
2. Trace / Artifact / Diff linkage is stable
3. end-to-end single-user runtime flow is regression-tested
4. storage-role meaning is consistently legible
5. proposal-flow boundaries remain intact

## 6. First Review-System Reentry Target

The first useful reentry surface is not full authority orchestration.
It is a bounded shared-review context surface.

Recommended first reentry order:
1. shared review context opening
2. anchored comments / annotations
3. issue lifecycle
4. reviewer authority / approval record expansion

## 7. Constraints During Reentry

1. review metadata must not become engine truth
2. shared review context must not collapse into personal workspace state
3. comments must stay anchored
4. issue lifecycle must remain separate from approval truth
5. approval authority must remain explicit and auditable

## 8. Final Statement

Review-system UI remains a later phase.
It should reenter only after the single-user runtime shell and observability shell are already coherent.