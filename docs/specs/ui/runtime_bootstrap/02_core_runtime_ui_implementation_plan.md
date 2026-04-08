# Core Runtime UI Implementation Plan

## Recommended save path
`docs/specs/ui/runtime_bootstrap/02_core_runtime_ui_implementation_plan.md`

## Purpose

This document defines the implementation plan for the Core Runtime UI milestone.

This is not a speculative architecture note.
This is the implementation-side companion to the scope lock.

Its purpose is to determine:

- build order
- dependency order
- integration order
- test order
- completion gates

for turning the six-module runtime shell into a real usable UI surface.

## Target modules

The implementation target is fixed:

- Shell
- Graph Workspace
- Inspector
- Validation
- Execution
- Storage

All implementation phases in this plan must serve that target.

## Implementation philosophy

### 1. Build the shell as an integration surface, not as six isolated demos
The runtime shell is not complete if six panels exist but do not form one connected workflow.

### 2. Preserve adapter/view-model boundaries
No implementation shortcut may bypass the established contract layer and directly bind raw engine internals into shell modules.

### 3. Keep invalid/incomplete drafts renderable
Working Save may remain incomplete or blocked.
The shell must not collapse just because the draft is imperfect.

### 4. Prefer integration slices over decorative completeness
A working selection → validation → run → status flow is more important than polished styling or peripheral UI chrome.

## Official implementation sequence

### Phase 1. Shell composition and global framing
Goal:
Create the real shell entrypoint and the stable high-level composition frame.

Required outcomes:
- official runtime shell entrypoint
- top-level layout with top/left/center/right/bottom or equivalent adaptive composition
- workspace identity and storage role display
- current mode/status strip
- placeholder-capable module slots
- stable route for global actions

Must be wired:
- workspace name / identity
- storage role badge
- global status summary
- top-level action cluster entrypoints

Not yet required in full depth:
- deep module functionality
- dense keyboard layer
- advanced observability surfaces

Completion check:
A user can enter the shell and understand what workspace they are in and what storage role they are looking at.

### Phase 2. Graph + selection + inspector loop
Goal:
Close the first real operational loop:
graph selection → selected object projection → inspector detail.

Required outcomes:
- graph renders current structure
- graph renders incomplete/invalid drafts
- selection state is stable
- selected object adapter slice feeds the inspector
- inspector distinguishes read-only and editable surfaces
- inspector can emit bounded edit intent

Must be wired:
- node selection
- edge selection where applicable
- selection summary
- inspector field groups
- edit-intent emission path

Completion check:
A user can click a graph object and reliably inspect it without the shell losing lifecycle context.

### Phase 3. Validation integration
Goal:
Attach validator surfaces as a first-class operational module, not a later add-on.

Required outcomes:
- validation summary visible
- blocked vs warning vs confirmation_required is distinct
- findings map back to graph/object targets
- suggested next actions visible
- shell remains usable when draft is blocked

Must be wired:
- validation summary counts
- blocking findings list
- warning findings list
- target highlighting or navigation hooks
- explicit explanation of why action is blocked

Completion check:
A user can understand why a draft cannot proceed and where the problem lives.

### Phase 4. Execution integration
Goal:
Attach real execution status to the shell so the UI can request runtime action and read runtime state.

Required outcomes:
- run request path wired
- queued/running/completed/failed/partial/cancelled visible
- current execution summary visible
- active node or equivalent execution context visible
- latest output summary visible

Must be wired:
- run action
- execution status model
- recent event summary
- failure summary
- run controls only where valid

Completion check:
A user can request execution and see honest execution state from the same shell.

### Phase 5. Storage integration
Goal:
Attach storage lifecycle clarity so the user always knows draft vs approved vs history position.

Required outcomes:
- current storage role visible
- working draft state visible
- anchor to approved snapshot visible when relevant
- execution record relationship visible when relevant
- shell avoids save/commit confusion

Must be wired:
- storage role projection
- “has uncommitted changes” or equivalent draft state
- latest commit snapshot reference summary
- run anchor reference summary

Completion check:
A user can tell whether they are editing a draft, reading approved structure, or looking at execution history.

### Phase 6. End-to-end runtime shell closure
Goal:
Close the six-module shell as one integrated operational product slice.

Required outcomes:
- graph + inspector + validation + execution + storage all stay coherent in one shell
- shell survives blocked/incomplete/partial states
- action boundaries remain intent/action based
- lifecycle boundaries remain visible
- no module needs to fake engine truth to stay useful

Completion check:
A realistic user can open a draft, inspect it, understand issues, request execution, and read current lifecycle state without leaving the shell.

## Required cross-module data flows

The following flows must exist before the runtime shell is considered real.

### A. Graph → Inspector
- graph selection changes
- selected object view model updates
- inspector updates
- inspector emits edit intent

### B. Inspector → Validation
- edit intent is evaluated by engine/validator
- validation surface updates
- any affected object/location is linkable back to graph

### C. Execution → Graph / Validation / Storage
- execution state updates
- graph can show active/failing state at operational level
- validation can surface execution guard or runtime failures when relevant
- storage surface can show run anchor context

### D. Storage → Shell framing
- storage role influences how surfaces are labeled and interpreted
- shell never treats all states as generic “saved”

## Testing order

### 1. Composition tests
- shell loads with all module slots
- shell survives missing/partial slices
- shell layout does not require perfect draft state

### 2. Selection tests
- graph selection updates inspector
- selection survives module refreshes
- invalid nodes remain inspectable

### 3. Validation tests
- blocked/warning/confirmation_required distinctions render correctly
- findings can be navigated back to targets
- blocked state prevents invalid next-step affordances from appearing as available

### 4. Execution tests
- execution state is taken from engine events/records only
- failed/partial/cancelled states remain visible
- no fake success UI is shown without engine evidence

### 5. Storage tests
- Working Save / Commit Snapshot / Execution Record labels remain distinct
- save/commit confusion is not introduced by the shell
- storage-context summaries remain truthful

### 6. End-to-end tests
- open draft → select → inspect → see blocked validation → fix intent → request run → read execution summary
- open invalid draft → still render graph and inspector → still show validation explanation
- open run-related context → show execution status without claiming structural mutability

## Non-goals during implementation

Do not fold in the following during this plan unless strictly required for the six-module shell.

- deep collaboration features
- review thread systems
- issue lifecycle depth
- authority/governance UI
- full trace explorer depth
- full artifact explorer depth
- rich diff workbench

Those belong to later documents.

## Completion gate

The Core Runtime UI milestone is complete only if all of the following are true at once:

1. the shell is real, not just specified
2. the graph is operationally useful
3. the inspector is connected
4. validation is first-class
5. execution is first-class
6. storage lifecycle is visible
7. invalid drafts still render
8. engine truth boundaries remain preserved

## Final rule

The implementation plan must be judged by integrated user capability, not by number of UI files or isolated view models.
The six-module runtime shell is the product slice that matters now.
