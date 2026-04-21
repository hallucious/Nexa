# Beginner Shell Compression Policy

## Recommended save path
`docs/specs/ui/beginner_shell_compression_policy.md`

## 1. Purpose

This document defines the official beginner-shell compression policy for Nexa.

Its purpose is to ensure that a first-time non-technical user can achieve a meaningful first success without learning Nexa's internal engine model, while preserving all core engine contracts and architectural invariants.

This policy does not change engine truth.
It only changes what is shown, when it is shown, and how it is named in the beginner-facing shell.

## 2. Core Principle

The beginner shell is not a simplified engine.
It is a compression layer that delays the exposure of engine complexity until the user is ready for it.

In short:

The engine remains structurally rich.
The beginner-facing surface becomes progressively understandable.

## 3. Non-Negotiable Boundary

The following remain unchanged:

- engine contracts
- architecture constitution
- storage truth
- approval truth
- execution truth
- proposal-first governance flow

This policy affects only:

- display
- naming
- routing
- progressive disclosure
- default panel visibility
- onboarding sequence

## 4. Compression Rules

### 4.1 Storage role terminology
Working Save, Commit Snapshot, and Execution Record must be hidden during the first session.

Beginner-visible surface:
- saved
- not saved

The internal storage-role model remains unchanged in the engine.

### 4.2 Trace / Diff / History
Trace, diff, execution history, and provenance-heavy observability surfaces must be deferred until after first success.

These surfaces are valid and important, but they are not first-session surfaces.

### 4.3 Validation
Beginner validation must not be reduced to status-only signaling.

The official beginner validation format is:

- status signal
- one-sentence cause
- one clear next action

Examples:

- Cannot run yet. Step 2 has no AI model selected. [Fix Step 2]
- Ready, but needs confirmation. Output format is not specified. [Run with default] [Change settings]
- Ready to run. [Run]

The beginner shell must never show raw validator internals by default.

### 4.4 Designer input
When a workspace is empty, the default visible primary surface must be the Designer input.

A beginner should not need to discover a separate Designer panel before they can begin.

### 4.5 Proposal governance
The full internal flow remains:

Intent -> Patch -> Precheck -> Preview -> Approval -> Commit

But in the beginner shell, this must appear as a single visible confirmation moment.

Beginner-visible pattern:
- Here is what I will build
- Looks good?
- Approve / Revise

The engine still executes the full governance chain.

### 4.6 Terminology remapping
In the beginner shell, engine-facing terminology must be replaced by user-facing display language.

Official beginner display mapping:

- Circuit -> Workflow
- Node -> Step
- Provider -> AI model

This is a display-layer rule only.
Internal contracts and implementation names remain unchanged.

### 4.7 Graph view timing
The graph view must not be the first primary surface shown to a beginner in their first session.

The graph may appear after the first workflow has been generated or after first success, but it must not be the first required interaction surface in the beginner's first session.

Graph may remain visible as a structural anchor in a reduced or secondary role.

### 4.8 Advanced surface unlocking
Advanced surfaces must unlock progressively only after either:

1. the user achieves first success
2. the user explicitly requests deeper control

This prevents two failure modes:

- the beginner shell becoming a permanent simplification cage
- advanced surfaces leaking too early and collapsing the compression strategy

## 5. First-Session Target Flow

The intended first-session flow is:

1. Empty workspace opens
2. Designer input is front and center
3. User describes goal in plain language
4. Nexa shows a plain-language build preview
5. User approves
6. Nexa creates the workflow
7. User runs it
8. Nexa shows result
9. Optional deeper surfaces become available later

A beginner must be able to succeed without seeing:
- storage-role terminology
- raw validator findings
- trace timeline
- diff viewer
- deep history
- engine identifiers
- provider references
- governance internals

## 6. Implementation Meaning

This policy is implemented through shell behavior, not engine redesign.

Primary implementation levers:

- default panel routing
- default empty-workspace state
- visibility gating
- display-text substitution
- progressive disclosure rules
- unlock conditions
- beginner/advanced shell enforcement

## 7. Practical Summary

The beginner shell compression policy is:

- hide internal storage/runtime terminology in the first session
- delay deep observability until after first success
- compress validation into:
  status + one-sentence cause + one clear next action
- make Designer input the default empty-workspace surface
- compress proposal governance into one visible confirmation moment
- rename engine-facing terms into user-facing display language
- introduce graph view after first success or after workflow creation
- unlock advanced surfaces only after first success or explicit request

## 8. Final Statement

The beginner shell does not weaken Nexa.

It preserves the full engine and architecture while controlling the order in which complexity becomes visible.

That is the official meaning of compression in Nexa UI.