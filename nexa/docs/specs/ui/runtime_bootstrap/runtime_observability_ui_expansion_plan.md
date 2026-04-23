# Runtime Observability UI Expansion Plan

## Recommended save path
`docs/specs/ui/runtime_bootstrap/runtime_observability_ui_expansion_plan.md`

## 1. Purpose

This document defines the next UI expansion step after core runtime shell closure.

Its purpose is to integrate already-existing observability modules into the runtime shell as first-class linked surfaces.

## 2. Scope

This plan covers:

1. Trace / Timeline Viewer
2. Artifact Viewer
3. Diff Viewer

It does not reopen the immediate runtime closure set.
It starts only after the 6-module runtime shell is coherent.

## 3. Core Decision

Observability modules already exist as implemented UI foundation surfaces.
The remaining work is not “invent them.”
The remaining work is:

- shell linkage
- cross-panel navigation coherence
- end-user readability
- observability-first recovery paths

## 4. Integration Priorities

### Priority 1 — Trace / Timeline Linkage

Reason:
temporal observability is the first required extension of Execution.

Required linkages:
- Execution → Trace / Timeline jump
- Graph active/failed node ↔ relevant trace slice
- Validation/runtime anomalies ↔ relevant execution slice
- shell summary ↔ latest significant run event

Expected outcome:
Trace becomes the temporal explanation surface of Execution,
not an isolated specialist panel.

### Priority 2 — Artifact Linkage

Reason:
artifacts are evidence surfaces, not just outputs.

Required linkages:
- Execution latest outputs ↔ Artifact Viewer
- Graph producing node ↔ relevant artifact
- Trace event ↔ artifact evidence
- selected object ↔ related artifact summaries where relevant

Expected outcome:
Artifact Viewer becomes the evidence-reading companion to Execution and Trace.

### Priority 3 — Diff Linkage

Reason:
diff becomes most useful when connected to storage and proposal interpretation.

Required linkages:
- Storage ↔ structural diff
- Designer preview ↔ preview diff
- Graph changed objects ↔ diff focus
- run-to-run or snapshot-to-snapshot comparison entry points where supported

Expected outcome:
Diff becomes an active comparison surface,
not a detached textual delta screen.

## 5. Cross-Surface Linkage Rules

1. Graph remains the navigation anchor.
2. Observability panels must jump back to graph-relevant objects when possible.
3. Execution truth remains engine-owned.
4. Trace / Artifact / Diff panels must not invent missing evidence.
5. Observability linkage is about surfacing and navigation, not new truth creation.

## 6. Beginner / Advanced Interpretation

### Beginner
- observability remains partially collapsed by default
- only most relevant trace/artifact/diff summaries surface automatically
- full deep panels open on demand

### Advanced
- trace/artifact/diff may stay pinned or open together
- richer observability density is allowed
- cross-panel comparison can be stronger

## 7. Completion Criteria

Observability expansion is complete only when:

- user can move from execution status to trace explanation quickly
- user can move from outputs to artifacts quickly
- user can move from storage/proposal changes to diff quickly
- graph linkage remains intact across all three surfaces
- observability surfaces feel integrated into one shell rather than bolted-on extras

## 8. Final Statement

The next observability step is not module invention.
It is **Trace / Artifact / Diff shell linkage closure**.