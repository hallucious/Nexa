# CURRENT_IMPLEMENTATION_STATE

Version: 1.2.0

## Purpose

This document is the short-form implementation truth sheet for the current repository state.

It exists to answer four practical questions quickly:

1. What is already implemented in code?
2. What is only partially converged?
3. What should not be reopened casually?
4. What should happen next after the `d468795` truth sync?

This document is intentionally implementation-first.
It is not a replacement for the detailed architecture/spec documents.

## Authoritative Snapshot

- authoritative implementation baseline commit: `d468795`
- authoritative verified baseline: `2087 passed, 13 skipped`
- status source: latest repository snapshot used in the current handoff baseline (`Nexa_d468795.zip`)
- canonical macro roadmap reference: `nexa_implementation_order_final_v2_2.md`
- practical phase interpretation: **Phase 4.5 server/product continuity build-out already broadly present in code**

## One-Line Position

Nexa at `d468795` is no longer mainly a “provider probe persistence not yet closed” repository; it is already a broad Phase 4.5 server/product continuity codebase whose top-level status documents previously lagged behind the actual source.

## Sector Matrix

| Sector | Status | Notes |
|---|---|---|
| execution engine core | Complete baseline | dependency-based runtime, provider/plugin execution, observability, savefile execution, and artifact/trace foundations remain in place |
| storage role split (`working_save` / `commit_snapshot`) | Complete baseline | role-aware `.nex` loading/validation/model split remains implemented |
| UI adapter / view-model layer | Complete baseline | Core 5 + expanded shell/view-model surfaces remain present |
| UI persistence / storage boundary | Complete baseline | Working Save may carry UI continuity; Commit Snapshot must not carry canonical `ui` |
| UI i18n foundation | Complete baseline | localized lookup, fallback, EN/KO resources, and persistence boundary remain implemented |
| Designer proposal-flow projection | Implemented baseline | session-state / proposal / preview / approval projection remains present |
| Subcircuit foundation | Implemented baseline | parser / validator / runtime / roundtrip / example coverage remain present |
| server database / migration foundation | Implemented baseline | canonical Phase 4.5 schema families now exist in `src/server/database_foundation.py` |
| workspace / onboarding continuity API | Implemented baseline | workspace registry and onboarding continuity families are already wired into server services/models/routes |
| run admission / run read / run list continuity API | Implemented baseline | launch + list + status/result surfaces exist and carry continuity summaries |
| artifact / trace continuity API | Implemented baseline | run artifact detail/list and trace read surfaces exist |
| provider operational continuity API | Implemented baseline | provider catalog / binding / secret / health / probe / probe-history surfaces exist |
| aggregate continuity projection | Implemented baseline | recent activity / history summary and multiple adjacent surfaces already expose normalized continuity views |
| route / framework / FastAPI bindings | Implemented baseline | route surface, framework binding, and FastAPI binding already expose the current server family |
| managed secret authority integration | Implemented baseline | AWS Secrets Manager binding exists for managed-secret authority integration |
| general-user productization | Not active implementation truth | canonical roadmap still prioritizes beginner-shell / first-success / return-use, but this code baseline is more advanced in server continuity than in product closure |

## Stable Enough To Stop Reopening

The following should now be treated as closed-enough baseline decisions unless a real contradiction is found in source.

### 1. Provider probe persistence foundation

- `provider_probe_events` is already part of the database foundation
- provider probe execution and provider probe history surfaces both already exist
- further work should not pretend the project is still at the “invent probe persistence” stage

### 2. Broad continuity projection family

- continuity is already projected across workspace, onboarding, run, artifact/trace, provider, aggregate, user-scope, and setup-entry-adjacent server surfaces
- accepted/read/rejected responses are increasingly symmetrical around shared continuity summaries
- future work should inventory remaining edge cases rather than reopen the existence of the continuity family itself

### 3. Macro roadmap vs practical code-state distinction

- `nexa_implementation_order_final_v2_2.md` remains the canonical dependency roadmap
- the actual code at `d468795` is already deep inside the Phase 4.5 continuity track
- both statements must remain visible simultaneously

### 4. UI/storage/designer foundations

- the older UI-sector convergence work remains real and implemented
- the newer server continuity work does not invalidate those foundations
- future status documents must keep both lines visible instead of replacing one with the other

## Must Remain Open

The following are still open and should not be overclaimed.

### 1. Remaining edge / exception continuity gaps

Some lower-frequency rejection, exception, admin, collaboration, or non-happy-path surfaces may still fall outside the normalized continuity family.
These should be found explicitly, not guessed.

### 2. Route / binding / export drift risk

Every future server seam still risks missing updates in:

- `src/server/http_route_surface.py`
- `src/server/framework_binding.py`
- `src/server/fastapi_binding.py`
- `src/server/__init__.py`

### 3. General-user productization track

The product roadmap priorities for beginner-shell enforcement, first-success blockers, and return-use loop are still open work even though the current codebase is ahead on server continuity.

## Reopen-Prohibited Topics

Do not casually reopen the following:

- whether provider probe persistence exists yet
- whether the server already has a broad continuity projection family
- whether the codebase is still mainly at the old `c869806` status line
- whether `.nex.ui` may become canonical snapshot truth
- whether UI foundations must be re-theorized before any further server/product work

## Keep-Open Topics

Continue treating the following as active implementation topics:

- remaining-gap inventory for edge/exception server surfaces
- narrow next seam selection after the truth sync
- general-user productization work when it becomes the active line again
- route/binding/export integrity for every new server-facing change

## Recommended Immediate Next Batch

The most rational immediate next batch after this truth sync is:

**build a real remaining-gap inventory for the Phase 4.5 continuity family and choose only one clearly justified bounded seam from that inventory.**
