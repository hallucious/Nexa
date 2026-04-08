# Runtime Observability UI Expansion Plan

## Recommended save path
`docs/specs/ui/runtime_bootstrap/03_runtime_observability_ui_expansion_plan.md`

## Purpose

This document defines the first expansion that should follow immediately after the six-module runtime shell closes.

Its purpose is to move Nexa from:

**a runtime-capable shell**

to

**a runtime-observable control plane**

The expansion layer focuses on the operational surfaces that explain what happened, why it happened, and what evidence was produced.

## Why this comes next

Nexa is not only an editor.
It is an execution engine product.

That means the UI becomes substantially more valuable only when execution observability is real.
If the shell can request execution but cannot deeply explain runtime behavior, the experience remains only partially closed.

Therefore the next expansion after the core runtime shell is not collaboration depth.
It is observability depth.

## Expansion modules

The primary expansion modules are:

- Trace / Timeline Viewer
- Artifact Viewer
- Diff Viewer

Storage remains relevant here, but it already belongs to the core runtime shell because lifecycle clarity is foundational.

## Core observability decision

The shell must evolve from “can run” to “can explain runs”.

This means the UI must be able to project:

- event stream
- temporal ordering
- runtime failure linkage
- artifact production and lineage
- comparison surfaces across draft/snapshot/run states

without fabricating history or flattening engine-owned provenance.

## Phase 1. Trace / Timeline integration

### Goal
Make execution history readable as history, not just as a single latest-status summary.

### Required outcomes
- event stream surface exists
- node/resource events are visible in order
- active/failing slices can be inspected
- retries/replays are distinguishable when available
- trace items can jump back to graph/object context

### Why it matters
Without a trace surface, failure explanation remains shallow.
A status badge cannot replace a temporal history surface.

### Minimum connected flow
- run happens
- execution panel shows summary
- trace viewer exposes recent events/timeline
- selected trace event can highlight or reference graph/object context

### Completion check
A user can answer not only “did it fail?” but also “where in the sequence did it fail and what happened right before it?”

## Phase 2. Artifact integration

### Goal
Make produced evidence inspectable as artifacts, not merely as generic output blobs.

### Required outcomes
- artifact summary list exists
- intermediate vs final artifacts are distinguishable
- artifact preview/detail surface exists
- artifact can link back to producing execution context
- append-only provenance remains visible

### Why it matters
Nexa treats artifacts as first-class evidence.
If the UI collapses them into opaque output strings, a large part of runtime truth becomes invisible.

### Minimum connected flow
- run produces artifact
- execution summary references artifact availability
- artifact viewer shows summary/preview
- artifact links back to node and/or trace context

### Completion check
A user can inspect what was produced and where it came from.

## Phase 3. Diff integration

### Goal
Make meaningful comparison surfaces available for runtime and proposal work.

### Required outcomes
- draft vs commit comparison available
- preview vs current comparison available
- run vs run comparison direction available where supported
- source and target remain explicit
- diff links back to graph/object context

### Why it matters
Nexa increasingly depends on comparison:
- what changed in the structure
- what changed in the proposal
- what changed between runs

A runtime UI without comparison becomes operationally shallow.

### Minimum connected flow
- open diff surface
- understand source and target
- inspect changed object scope
- jump back to graph/object anchor

### Completion check
A user can see what changed without confusing preview, draft, approved structure, and runtime history.

## Phase 4. Cross-link closure

### Goal
Stop trace, artifact, diff, execution, graph, and validation from feeling like isolated panes.

### Required outcomes
- trace item can lead to graph/object context
- artifact can lead to producing node or event context
- diff item can lead to changed graph/object context
- execution summary can lead to trace/artifact surfaces
- validation can reference runtime-related failures where applicable without collapsing categories

### Completion check
The observability surfaces feel like one investigation loop, not five detached tabs.

## What this phase must not do

### 1. It must not fabricate runtime truth
UI cannot invent missing events, synthetic lineage, or convenient success states.

### 2. It must not reinterpret storage role boundaries
Execution Record remains execution history.
Commit Snapshot remains approved structural anchor.
Working Save remains draft context.

### 3. It must not become collaboration depth by accident
Comments, review threads, authority records, and shared review workflows remain later work.

## Suggested implementation order

1. Trace / Timeline Viewer minimal slice
2. Artifact Viewer minimal slice
3. cross-links between Execution ↔ Trace ↔ Artifact
4. Diff Viewer minimal slice
5. cross-links between Graph ↔ Diff ↔ Validation ↔ Execution
6. richer failure / replay / lineage depth if needed

## Completion gate

The observability expansion is complete when:

- the shell can explain execution history beyond a single status line
- artifacts are visible as first-class evidence
- diff surfaces clarify structural/proposal/runtime changes
- the main operational investigation loop is coherent

## Final rule

After the core runtime shell closes, observability is the highest-value expansion.
It must come before collaboration depth because Nexa’s core product value is execution intelligibility, not comment-thread richness.
