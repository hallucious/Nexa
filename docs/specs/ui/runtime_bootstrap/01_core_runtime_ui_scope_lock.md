# Core Runtime UI Scope Lock

## Recommended save path
`docs/specs/ui/runtime_bootstrap/01_core_runtime_ui_scope_lock.md`

## Purpose

This document fixes the official current implementation target for the next UI phase of Nexa.

The current target is not “general UI maturity”.
The current target is not “deeper review-system sophistication”.
The current target is:

**a real runtime-capable shell built around six tightly connected modules**

- Shell
- Graph Workspace
- Inspector
- Validation
- Execution
- Storage

This document exists to prevent scope drift while the runtime shell is being turned into a real product surface.

## Core decision

The current UI milestone is:

**Core Runtime UI**

This milestone is complete only when a user can do the following in one connected shell:

1. open or continue a Working Save
2. see the graph structure
3. select nodes/edges/outputs and inspect them
4. understand blocked / warning / confirmation-required state
5. request execution
6. observe execution status and latest outputs
7. understand current storage role and lifecycle position

The milestone is not complete merely because contracts, mockups, or isolated panel specifications exist.

## Why this is the right next target

Nexa already has meaningful UI foundation work.
The next bottleneck is not “more architecture discussion”.
The next bottleneck is integrating graph, selection, validation, execution, and storage into a runtime-capable shell.

The shell must still preserve the established architectural boundary:

- engine owns structural truth
- engine owns approval truth
- engine owns execution truth
- engine owns storage lifecycle truth
- UI projects those truths through adapter/view-model boundaries
- UI emits intents/actions instead of mutating raw truth

Therefore the next step is not new truth systems.
The next step is shell closure.

## In-scope modules

### 1. Shell
The top-level workspace shell is in scope.

Responsibilities:
- provide the overall runtime workspace layout
- surface workspace identity
- surface storage role
- surface mode/status context
- host the six-module composition
- route keyboard / navigation / global actions
- keep module composition coherent

Not allowed:
- owning structural truth
- owning execution truth
- flattening storage lifecycle
- bypassing adapter/view-model boundaries

### 2. Graph Workspace
The graph is in scope because it is the primary structural anchor.

Responsibilities:
- show circuit structure
- show selection
- show current state overlays at an operational level
- remain renderable even for incomplete/invalid drafts
- act as navigation anchor into Inspector/Validation/Execution/Storage context

Not allowed:
- inventing execution order
- silently mutating structure
- visually implying commit/approval that does not exist

### 3. Inspector
The inspector is in scope because selection without detail is not operationally useful.

Responsibilities:
- project the selected object
- distinguish read-only from editable surfaces
- emit bounded edit intent
- expose related warnings/constraints
- act as the official node/object detail surface

Not allowed:
- direct mutation of engine-owned fields
- silent bypass of validation
- raw editor state becoming truth

### 4. Validation
Validation is in scope and is mandatory.

This is an important correction:
Validation must not be treated as “later review work”.
Validation is a runtime-shell safety surface.

Responsibilities:
- show pass / warning / confirmation_required / blocked
- explain why commit or execution is blocked
- map findings to graph/object targets
- expose next-step hints
- distinguish hard blockers from softer risks

Not allowed:
- silently fixing structure
- suppressing engine blockers
- being collapsed into generic error presentation

### 5. Execution
Execution is in scope because the shell must be able to operate the engine, not merely edit structure.

Responsibilities:
- show idle / queued / running / completed / failed / partial / cancelled
- show active node/current progress
- show latest result summary
- expose bounded run controls when allowed
- remain anchored to engine events and records

Not allowed:
- inventing success/failure states
- fabricating execution history
- turning UI simulation into execution truth

### 6. Storage
Storage is in scope because users must understand where they are in the lifecycle.

Responsibilities:
- show current storage role
- show relationship between Working Save / Commit Snapshot / Execution Record
- show whether the current draft is uncommitted
- show where execution is anchored
- expose bounded storage actions when allowed

Not allowed:
- flattening storage roles into a generic “saved state”
- hiding lifecycle boundaries
- letting UI continuity masquerade as canonical truth

## Official minimum capability set

The six-module runtime shell must minimally support the following connected flows.

### A. Open and orient
- open Working Save
- show workspace identity
- show storage role
- render graph
- render current selected-object surface

### B. Inspect and understand
- click/select graph objects
- update inspector
- update validation references
- keep partial/invalid drafts renderable
- show what is blocked and why

### C. Request action
- emit edit intent
- emit run request
- emit save/review/commit-adjacent bounded actions only where valid
- respect current storage role and validation state

### D. Observe runtime status
- show current execution status
- show latest execution summary
- show operational failure without inventing history
- remain usable during incomplete/failed/partial states

### E. Read lifecycle boundaries
- make Working Save / Commit Snapshot / Execution Record distinction visible
- make “draft vs approved vs history” visible
- prevent save/commit confusion in the shell itself

## Explicitly out of scope for this milestone

The following are not part of the current core-runtime-shell closure.

### Deferred review/collaboration system
- shared review view
- comments / annotations / review threads
- issue lifecycle management
- reviewer authority and approval governance depth
- collaboration-specific resolution workflows

### Deep observability expansion
- full trace timeline depth
- full artifact lineage explorer
- rich diff comparison surfaces
- dense metrics dashboards
- replay-oriented investigation surfaces

### UI-only overreach
- UI-driven truth reinterpretation
- UI-first freezing of unfinished engine APIs
- frontend work that hard-locks unstable engine boundaries
- speculative UX layers that imply engine functionality not yet wired

## Relationship to later work

This scope lock does not say that Trace / Artifact / Diff are unimportant.
It says they are the next layer after the six-module shell closes.

The intended order is:

1. Core Runtime UI Scope Lock
2. Core Runtime UI Implementation
3. Runtime Observability Expansion
4. Review System Reentry

## Completion criteria

The scope lock is considered satisfied in implementation only when the runtime shell can demonstrate all of the following:

- a user can open a working draft
- the graph renders even when incomplete
- selecting graph objects updates the inspector
- validation explains blocked/warning state
- execution can be requested from the shell
- execution status is visible in the shell
- storage role and lifecycle boundaries remain visible
- the shell still respects engine-owned truth boundaries

## Final rule

The current official UI target is the six-module runtime shell.

Anything that does not help close that shell is secondary right now.
Anything that weakens engine truth boundaries is forbidden right now.
