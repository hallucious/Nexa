# Review System Reentry Plan

## Recommended save path
`docs/specs/ui/runtime_bootstrap/04_review_system_reentry_plan.md`

## Purpose

This document defines when and how the deferred review/collaboration system should re-enter the implementation roadmap after the runtime shell and observability layers are in place.

Its purpose is to prevent two opposite mistakes:

1. returning to review-system depth too early
2. postponing review-system reintegration so long that proposal/approval work becomes fragmented later

This plan therefore defines:

- reentry conditions
- reentry order
- protected boundaries
- scope for the first review-system return

## Why review is deferred now

The review/collaboration layer is important, but it is not the correct next implementation priority.

The reason is simple:
the runtime shell itself must first become real.

Before reentry, the product must already have:

- a usable runtime shell
- a visible validation surface
- a visible execution surface
- visible storage lifecycle boundaries
- meaningful observability surfaces for runs and outputs

Without those, review-system work becomes detached from the actual operational core.

## Reentry preconditions

The review-system track should not resume until all of the following are true.

### 1. Core runtime shell is closed
Meaning:
- Shell + Graph + Inspector + Validation + Execution + Storage are operationally integrated

### 2. Basic observability loop is closed
Meaning:
- Trace / Timeline minimal surface exists
- Artifact Viewer minimal surface exists
- at least minimal diff/comparison direction exists

### 3. Storage and approval boundaries remain intact
Meaning:
- review-system work will not be used to flatten Working Save / Commit Snapshot / Execution Record semantics
- UI still does not own approval truth

### 4. Proposal flow is already visible enough to attach review meaningfully
Meaning:
- Designer proposal/precheck/preview surfaces exist sufficiently for review to bind to them

If these are not true, review reentry is premature.

## First reentry target

The first reentry target is not the entire governance system.
The first reentry target should be:

**shared review context over existing proposal/runtime surfaces**

This means the first return should focus on attaching collaborative review meaning to already-operational surfaces, not creating a parallel review universe.

## Reentry order

### Phase 1. Shared review view
Reintroduce:
- standard shared review preset/context
- shareable focus into proposal/diff/findings/run slices
- standard review-oriented shell entry

Reason:
This is the lightest collaboration layer that still adds real value.

### Phase 2. Comments / annotations / review threads
Reintroduce:
- anchored comments
- shared vs personal distinction
- review-thread surfaces attached to existing objects

Reason:
Once shared review context exists, anchored discussion becomes meaningful.

### Phase 3. Issue lifecycle
Reintroduce:
- issue promotion
- lifecycle states
- resolution states
- linkage to findings/threads/targets

Reason:
This turns discussion into tracked review work, but only after anchored review discussion exists.

### Phase 4. Approval authority / decision record depth
Reintroduce:
- explicit approval decision record
- reviewer vs approver distinction
- authority scopes
- commit authorization visibility

Reason:
This is the deepest governance layer and should come last in the reentry chain.

## Things that must remain separated during reentry

### 1. Review metadata vs engine truth
Comments, issues, and review threads remain review metadata.
They must not become structural truth or execution truth.

### 2. Resolution vs approval
Resolving an issue is not the same as approving a patch or authorizing a commit.

### 3. Personal view state vs shared review context
Personal pins, personal density, and personal UI taste remain local.
Shared review context must stay canonical enough for cross-user use.

### 4. Validation vs collaboration
Validation remains a first-class runtime shell module.
It must not be reclassified as “just review”.

## First reentry deliverable set

When reentry begins, the first implementation slice should include only:

- shared review view entry
- shareable focus to proposal/diff/finding/run context
- anchored shared comments on selected core targets
- no deep governance yet
- no heavy authority matrix yet

This keeps reentry incremental.

## What must still remain deferred even after reentry begins

Even after review reentry starts, the following should not jump ahead too aggressively:

- complex reviewer-role matrices beyond what current product use actually needs
- large-scale issue governance before anchored discussion proves useful
- excessive approval workflow bureaucracy
- review-only data models that are not grounded in real proposal/runtime surfaces

## Reentry completion criteria for the first review return

The first review return is successful when:

- users can open a shared review context tied to real runtime/proposal surfaces
- users can comment on anchored objects
- users can distinguish shared discussion from local UI state
- approval remains explicit and separate
- review enriches the shell without hijacking the runtime core

## Final rule

The review system should come back after the runtime shell and observability loops are real.

When it comes back, it must attach itself to real operational surfaces, not replace them.
