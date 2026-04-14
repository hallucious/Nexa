# CURRENT_IMPLEMENTATION_STATE

Version: 1.4.0

## Purpose

This document is the short-form implementation truth sheet for the current repository state.

It exists to answer four practical questions quickly:

1. What is already implemented in code?
2. What is only partially converged?
3. What should not be reopened casually?
4. What should happen next after the current Phase 8 closure baseline?

This document is intentionally implementation-first.
It is not a replacement for the detailed architecture/spec documents.

## Authoritative Snapshot

- authoritative implementation baseline commit: `ffc479d`
- authoritative verified baseline: `2285 passed, 14 skipped`
- status source: latest repository snapshot used in the current handoff baseline (`nexa_ffc479d.Zip`)
- closure references:
  - `docs/status/PHASE7_CLOSURE_AUDIT.md`
  - `docs/status/PHASE8_CLOSURE_AUDIT.md`
- practical phase interpretation: **Phase 4.5 continuity foundation plus Phase 7 return-use loop closure plus Phase 8 inclusion/product-completeness closure now present in code**

## One-Line Position

Nexa at `ffc479d` is no longer mainly a Phase 4.5 continuity repository and no longer only a Phase 7-closure repository; it now also includes the practical closure of the surfaced Phase 8 inclusion/product-completeness line, and top-level truth documents must reflect that newer reality.

## Sector Matrix

| Sector | Status | Notes |
|---|---|---|
| execution engine core | Complete baseline | dependency-based runtime, provider/plugin execution, observability, savefile execution, and artifact/trace foundations remain in place |
| storage role split (`working_save` / `commit_snapshot`) | Complete baseline | role-aware `.nex` loading/validation/model split remains implemented |
| UI adapter / view-model layer | Complete baseline | Core 5 + expanded shell/view-model surfaces remain present |
| UI persistence / storage boundary | Complete baseline | Working Save may carry UI continuity; Commit Snapshot must not carry canonical `ui` |
| UI i18n foundation | Complete baseline | localized lookup, fallback, EN/KO resources, and surfaced-path completeness remain implemented |
| Designer proposal-flow projection | Implemented baseline | session-state / proposal / preview / approval projection remains present |
| Subcircuit foundation | Implemented baseline | parser / validator / runtime / roundtrip / example coverage remain present |
| server database / migration foundation | Implemented baseline | canonical continuity schema families remain present |
| workspace / onboarding continuity API | Implemented baseline | workspace registry and onboarding continuity surface families remain wired |
| run / artifact / trace continuity API | Implemented baseline | launch / list / read / status / result / artifact / trace route families remain wired |
| provider operational continuity API | Implemented baseline | binding / secret / health / probe / probe-history families remain wired |
| aggregate continuity projection | Implemented baseline | recent activity and history summary product/API families remain present |
| Phase 7 return-use loop | Complete baseline | circuit library, result history, onboarding continuity alignment, and feedback channel are all present and closure-audited |
| Phase 8 inclusion / product completeness | Complete baseline | surfaced accessibility and Korean localization closure are implemented and closure-audited |
| product-facing terminology / metadata refinement | Complete baseline | major surfaced wording, metadata, and fallback cleanup batches have landed |
| Phase 9 (Stage 5 expansion line) | Open | public-boundary-first expansion remains next official work; accounts/sessions already belong to Phase 4.5 foundation |

## What Should Not Be Reopened Casually

### 1. Phase 7 closure

The return-use loop is closed enough to keep closed unless source or tests show a concrete contradiction.

### 2. Phase 8 closure

The surfaced inclusion/product-completeness line is closed enough to keep closed unless source or tests show a concrete contradiction.

### 3. The server continuity foundation

The repository already contains broad continuity foundations and should not be discussed as though that layer is still absent.

## What Still Remains Open

### 1. Phase 9 (Stage 5 product expansion)

The next official product-facing line after the current closure state is expansion work rather than continued Stage 4 cleanup.

### 2. Residual polish outside the surfaced path

Some older or less central wording/localization/accessibility debt may still exist, but that is no longer strong enough to keep Phase 8 open.

### 3. Route / binding / export integrity

Future new surfaces still need explicit alignment across route surface, framework binding, FastAPI binding, and package export layers.

## Immediate Practical Next Move

**Treat both Phase 7 and Phase 8 as closed at the `ffc479d` / `2285 passed, 14 skipped` baseline, keep their closure audits authoritative, and shift the next official implementation/planning line to Phase 9 (Stage 5 product expansion) instead of continuing narrow Phase 8 cleanup by habit.**
