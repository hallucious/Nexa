# Three State Wireframes v1

## Recommended save path
`docs/specs/ui/workspace_shell/04_three_state_wireframes.md`

## 1. Purpose

This document defines the three major foreground states of the same shell:

- Build
- Review
- Run

The shell remains one workspace.
Only emphasis changes.

## 2. Build state

Build is structure-edit-first.

### Foreground
- Graph dominant
- Inspector primary in Right Stack
- Validation visible in Bottom Dock
- Designer present but secondary

### What Build emphasizes
- node and edge creation
- group / zone organization
- inspector-based field editing
- validation visibility
- template use
- lens-based structural understanding

### Canonical Build read
The user is still shaping the draft.
The system should feel like a working canvas with immediate structural feedback.

## 3. Review state

Review is proposal-and-risk-first.

### Foreground
- Graph preview overlay on
- Designer primary in Right Stack
- Diff and Validation highly visible in Bottom Dock
- touched scope and destructive signals emphasized

### What Review emphasizes
- how the request was interpreted
- what changed
- what is risky
- what is blocked
- what requires confirmation
- approve / reject / request revision actions

### Canonical Review read
The user is not editing freely.
The user is judging a proposed future state.

## 4. Run state

Run is execution-observability-first.

### Foreground
- Graph with execution overlay
- Execution side panel primary
- Trace or Execution tab primary in Bottom Dock
- latest output summary visible

### What Run emphasizes
- what is currently running
- where execution is stuck
- what recently happened
- what outputs/artifacts were produced
- what failed or partially completed

### Canonical Run read
The user is watching and diagnosing the engine, not shaping structure.

## 5. The invariant

Across all three states:
- graph remains center
- storage role remains visible
- mode remains visible
- shell layout family remains recognizable

That invariant is mandatory.
If state switching makes the product feel like a different application each time, the design is wrong.
