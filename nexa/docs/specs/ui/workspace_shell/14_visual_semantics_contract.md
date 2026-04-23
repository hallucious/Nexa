# Visual Semantics Contract v1

## Recommended save path
`docs/specs/ui/workspace_shell/14_visual_semantics_contract.md`

## 1. Purpose

This document fixes the operational contract for color, badges, line styles, emphasis inside the Nexa shell.

It exists because Nexa is not a loose collection of panels.
It is one graph-centered workspace whose behavior must stay coherent across:
- Build
- Review
- Run
- Beginner density
- Advanced density

## 2. Core framing

The shell remains one shell.
Engine-owned truth remains outside UI ownership.
The contract here governs **presentation behavior and intent emission**, not raw truth mutation.

## 3. Main rules

### 3.1 Scope
This contract applies across the canonical shell:
- Top Bar
- Left Rail
- Graph Workspace
- Right Stack
- Bottom Dock

### 3.2 Invariants
- Graph remains the anchor
- storage role remains visible
- mode remains visible
- UI cannot silently redefine structural / approval / execution truth

### 3.3 State awareness
This contract is interpreted differently in:
- Build
- Review
- Run

and with different density in:
- Beginner
- Advanced

## 4. Detailed operational rules

### 4.1 Foreground vs background
The contract must define:
- what is primary
- what is visible
- what is collapsed
- what is hidden
- what is disabled

### 4.2 Wrong patterns to forbid
The contract must explicitly prevent:
- hidden truth mutation
- shell fragmentation into separate apps
- misleading metaphors that blur storage, approval, or execution boundaries
- silent transitions that hide the current operational state

## 5. Expected output of the contract

A correct implementation of this contract should make the shell:
- predictable for new users
- efficient for advanced users
- diagnosable under failure
- legible under dense runtime information
- stable under future UI replacement

## 6. Minimum v1 requirement

The first implementation must at minimum preserve:
- graph-centeredness
- explicit state labeling
- clear action boundaries
- safe relationship to Working Save / Commit Snapshot / Execution Record

## 7. Notes for implementation

This document belongs under the shell-design family rather than general UI miscellany because it constrains the operational grammar of the product, not just isolated widgets.

Implementation should treat it as a contract document, not a style suggestion.


## 8. Meaning axes

Visual language must distinguish:
- structural state
- validation state
- proposal / preview state
- execution state
- selection / focus state
- storage / role state

Color alone is forbidden as the sole carrier of meaning.
