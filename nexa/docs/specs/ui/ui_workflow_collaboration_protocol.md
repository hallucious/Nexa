# UI Workflow Collaboration Protocol v0.2

## Recommended save path
`docs/specs/ui/ui_workflow_collaboration_protocol.md`

## 1. Purpose

This document defines the official workflow and collaboration protocol for UI work in Nexa.

Its purpose is to make UI work:

- structurally safe
- engine-aligned
- reviewable
- iteration-efficient
- scalable across future UI modules
- resistant to ambiguity and drift across sessions

This protocol exists because Nexa UI work is not ordinary cosmetic frontend work.

Nexa UI must remain aligned with:

- engine-owned structural truth
- engine-owned approval truth
- engine-owned execution truth
- engine-owned storage lifecycle truth

At the same time, UI work must still support:

- visual review
- interaction design
- incremental prototype iteration
- human-readable feedback loops
- scalable module growth
- future replaceability of shells and panels

This document defines how UI work is actually performed between collaborators.

It is a workflow document, not a visual style guide and not a view-model contract.

## 2. Scope

This protocol governs:

- UI design iteration workflow
- prototype review workflow
- screenshot and annotation review workflow
- panel-level and screen-level review cycles
- documentation sync rules for UI work
- completion criteria for UI work
- change classification for UI work
- escalation rules when UI work affects engine or storage boundaries

This protocol does not replace:

- UI architecture package
- UI adapter / view-model contract
- per-module view-model specs
- `.nex.ui` schema rules
- engine-side storage or execution contracts

## 3. Position in the Nexa System

Official structural position remains:

Nexa Engine
-> UI Adapter / View Model Layer
-> UI Module Slots
-> Theme / Layout Layer

This workflow protocol operates above those rules.

Meaning:

- architecture documents define what UI is allowed to be
- contract documents define what data UI is allowed to read/write
- this protocol defines how UI work is created, reviewed, revised, and closed

This protocol must never be interpreted as permission to let workflow convenience override architectural boundaries.

## 4. Core Decision

UI work must be performed through explicit visual iteration loops rather than through abstract discussion only.

Official rule:

UI work in Nexa must proceed through bounded, evidence-bearing review units such as:

- textual wireframes
- static layout drafts
- interactive prototypes
- screenshots with numbered annotations
- module-specific review notes
- revision summaries

In short:

UI work is not finalized through verbal agreement alone.
UI work is finalized through explicit artifacts and bounded review rounds.

## 5. Core Principles

### 5.1 Engine Truth Boundary First
UI convenience must not redefine:

- structural truth
- approval truth
- execution truth
- storage truth

If a UI proposal appears to require changing those meanings, the change must be escalated into architecture/spec review before UI work continues.

### 5.2 Structure Before Aesthetics
The default order of work is:

1. meaning
2. information layout
3. interaction flow
4. state visibility
5. visual hierarchy
6. aesthetic refinement

The workflow must not begin with decorative styling if semantic layout is still unstable.

### 5.3 One Review Unit at a Time
A single review round should normally address one of the following:

- one screen
- one panel
- one core interaction
- one tightly coupled micro-flow

This rule exists to preserve clarity, reduce review noise, and increase iteration speed.

### 5.4 Visual Evidence Required
Feedback should be attached to one or more of the following:

- screenshot
- mockup
- wireframe
- prototype state
- numbered annotation
- side-by-side before/after

Purely verbal feedback may supplement review, but should not be the sole evidence when visual ambiguity exists.

### 5.5 Explicit Change Intent
Each UI revision must make it clear:

- what changed
- why it changed
- which module/screen it affects
- whether the change is structural, interactional, informational, or aesthetic
- whether related specs must also change

### 5.6 Scalability Over Local Convenience
UI decisions should favor scalable patterns over one-off local hacks.

When choosing between:
- a locally convenient special-case UI behavior
- a reusable module/pattern

the reusable pattern should be preferred unless it materially harms usability.

### 5.7 Replaceability Preservation
UI workflow must preserve both:

- whole-shell replaceability
- partial module replaceability

A review artifact or prototype may be highly specific, but the final structural rule should remain portable across shells/modules when possible.

### 5.8 Efficiency Through Narrow Iteration
Efficiency does not mean rushing.
Efficiency means minimizing wasted revision loops.

Therefore:

- the review unit must be narrow
- the problem statement must be explicit
- the success criteria must be visible
- unrelated concerns should not be mixed into the same round unless they are strongly coupled

### 5.9 Rational Escalation
Not every UI discomfort is a UI problem.

Some visual issues are caused by:
- missing engine status data
- missing adapter data
- unclear storage lifecycle exposure
- unclear approval/precheck exposure
- missing execution observability

If a UI issue is actually a missing lower-layer capability, it must be escalated instead of patched visually.

### 5.10 Draftability
UI work must remain productive even before the engine is fully complete.

Therefore, the workflow supports working with:

- mock data
- placeholder state
- simulated execution events
- draft previews
- partially defined module contracts

But these draft aids must remain explicitly non-authoritative.

## 6. Official Collaboration Layers

UI work is divided into five collaboration layers.

### 6.1 Layer A — Workflow / Use-Case Definition
Defines:

- who is using the screen
- for what purpose
- at what stage
- with what decision pressure
- with what risks if misunderstood

Outputs:
- use-case statement
- success scenario
- failure/confusion scenario
- target user mode (beginner / advanced / designer / reviewer / operator)

### 6.2 Layer B — Information Architecture
Defines:

- what information must be visible
- what can be secondary
- what should be hidden until requested
- what states must be surfaced immediately
- what the user must be able to compare

Outputs:
- field priority list
- panel responsibility map
- primary/secondary information structure
- visibility policy
- state exposure policy

### 6.3 Layer C — Interaction Architecture
Defines:

- what the user can do
- what the user can request
- what is read-only
- what requires confirmation
- what transitions between states

Outputs:
- action list
- interaction flow
- read-only vs intent-emitting boundaries
- confirmation points
- blocked/warning behavior

### 6.4 Layer D — Visual / Spatial Design
Defines:

- placement
- density
- grouping
- emphasis
- iconography
- affordance strength
- empty/loading/error/blocked appearance

Outputs:
- wireframe
- layout mock
- density mode proposal
- state appearance proposal
- visual hierarchy notes

### 6.5 Layer E — Refinement / Ergonomic Tuning
Defines:

- friction reduction
- repetitive action reduction
- scanning speed improvement
- layout polish
- spacing/contrast/clarity tuning
- advanced/beginner presentation adjustments

Outputs:
- revision pass
- before/after evidence
- ergonomic justification
- visual refinement notes

## 7. Official UI Work Units

UI work must be organized into bounded work units.

### 7.1 Screen Unit
A whole screen or main workspace surface.

Examples:
- Graph Workspace
- Full Designer Workspace
- Execution Dashboard

Use when:
- page-level or screen-level information layout is under review

### 7.2 Panel Unit
A single module slot or panel.

Examples:
- Inspector Panel
- Validation Panel
- Execution Panel
- Storage Panel

Use when:
- module-specific behavior or information density is under review

### 7.3 Interaction Unit
A bounded action-response sequence.

Examples:
- select node -> Inspector updates
- validation finding click -> graph highlights target
- approve patch -> snapshot creation summary appears

Use when:
- the main uncertainty is behavioral, not visual layout alone

### 7.4 State Unit
A single UI state rendered across one screen or panel.

Examples:
- empty state
- invalid draft state
- blocked precheck state
- long-running execution state
- partial trace state

Use when:
- the main risk is poor communication of status or consequences

### 7.5 Flow Unit
A short multi-step workflow crossing multiple panels/modules.

Examples:
- design request -> preview -> approval
- run -> observe -> inspect artifact
- compare working save vs commit snapshot

Use when:
- a single panel is insufficient to verify usability

## 8. Official Fidelity Levels

The workflow uses explicit fidelity levels.

### 8.1 L0 — Verbal Intent Only
Allowed only for:
- very early exploration
- quick scoping
- deciding what to prototype next

Not sufficient for:
- closing UI decisions
- finalizing layout
- finalizing interaction behavior

### 8.2 L1 — Text Wireframe
A text-only representation of layout and information placement.

Good for:
- fast structural review
- clarifying panel composition
- comparing layout ideas without overcommitting to visuals

Typical output:
- stacked region map
- left/right/top/bottom zone structure
- priority notes

### 8.3 L2 — Static Mockup
A non-interactive visual draft.

Good for:
- visual hierarchy
- grouping
- balance
- density review
- state visibility review

Typical output:
- image or screenshot
- annotated layout
- mock panel content

### 8.4 L3 — Interactive Prototype
A clickable or stateful prototype.

Good for:
- interaction review
- flow testing
- panel coordination
- transition comprehension
- realistic feedback loops

Typical output:
- rendered UI prototype
- multiple prototype states
- state switching examples

### 8.5 L4 — Implementation-Candidate Prototype
A prototype close enough to guide direct frontend implementation.

Good for:
- handoff to implementation
- behavior lock-in
- consistency checks against view-model contracts

Typical output:
- module-complete prototype
- stable interaction behavior
- implementation notes
- state coverage list

### 8.6 L5 — Production Polish Candidate
Used only when the structure and behavior are already stable.

Good for:
- aesthetic refinement
- spacing/contrast/polish
- accessibility tuning
- theme/layout tuning

Official rule:
L5 work must not be used to hide unresolved L1-L4 structural issues.

## 9. Official Iteration Order

Default order:

1. define use-case
2. define review unit
3. define success criteria
4. create L1 or L2 artifact
5. review with explicit feedback
6. revise
7. introduce L3 behavior if structure is stable
8. close the unit
9. sync documents/specs
10. move to next unit

This order may be compressed only when:
- the unit is very small
- the risk of misunderstanding is low
- the module pattern has already been established elsewhere

## 10. Standard Review Round Structure

Each UI review round should contain the following.

### 10.1 Round Header
- round id
- date/session reference
- target unit
- fidelity level
- related module(s)
- review focus

### 10.2 Input Context
- current goal
- prior round summary
- constraints
- what is intentionally not being solved in this round

### 10.3 Current Artifact
One or more of:
- wireframe
- static mockup
- interactive prototype
- screenshot set
- comparison view

### 10.4 Findings / Feedback
Feedback should be structured.

Preferred structure:
- location
- issue
- impact
- desired direction
- priority

### 10.5 Revision Decision
For each major issue:
- accept change
- reject change
- defer
- escalate to lower-layer spec/architecture review

### 10.6 Next-Round Goal
A single dominant next goal should be declared.

Examples:
- clarify validation severity hierarchy
- reduce graph workspace clutter
- improve run-state readability
- make approval flow safer
- align storage panel with snapshot lifecycle

## 11. Official Feedback Format

Feedback must be concrete and anchorable.

### 11.1 Required Structure
Each meaningful feedback item should include:

- target location
- observed problem
- why it is a problem
- proposed direction
- severity or priority

### 11.2 Preferred Anchoring Methods
Preferred anchors:
- screenshot number
- panel name
- region label
- element label
- annotated number marker
- state name

Example:

- Target: Graph Workspace / top-right action cluster / marker 3
- Problem: Run and Commit appear visually similar
- Impact: User may confuse execution with structural approval
- Direction: Increase separation and rename grouping
- Priority: High

### 11.3 Discouraged Feedback
The following are discouraged because they are too ambiguous:

- “Looks weird”
- “Feels off”
- “Make it prettier”
- “This is confusing” without identifying what is confusing
- “Change this part” without anchor or rationale

### 11.4 Feedback Severity
Recommended categories:
- Critical
- High
- Medium
- Low
- Cosmetic

### 11.5 Feedback Type
Recommended types:
- Structural
- Information hierarchy
- Interaction
- State communication
- Safety/clarity
- Aesthetic
- Accessibility
- Performance/complexity

## 12. Screenshot / Annotation Protocol

When reviewing screenshots or mockups, the following protocol is preferred.

### 12.1 Numbered Marker Rule
If multiple issues exist on one screen, they should be marked using visible numbers.

### 12.2 One Marker, One Main Issue
A single marker should normally represent one dominant issue.

### 12.3 State Labeling
The screenshot should indicate which state it represents.

Examples:
- Working Save / invalid
- Designer Preview / confirmation required
- Execution / running / partial output
- Storage / commit snapshot selected

### 12.4 Before/After Comparison Rule
If the change is iterative, a before/after pair should be preferred over isolated statements when feasible.

### 12.5 Partial Crop Rule
For dense screens, partial crops are acceptable if the target region is clearly identified.

## 13. Official Artifact Set Per UI Round

Every meaningful UI round should produce at least the following artifact set.

### 13.1 Mandatory
- primary artifact under review
- revision summary
- issue list or acceptance notes
- next goal

### 13.2 Preferred
- annotated screenshot
- alternative comparison if there are competing directions
- affected module list
- state coverage notes

### 13.3 Conditional
- prototype link or embedded prototype
- view-model implication note
- lower-layer escalation note
- spec sync requirement note

## 14. Change Classification System

Every UI change should be classified.

### 14.1 Class A — Cosmetic
Examples:
- spacing
- typography emphasis
- icon swap
- theme tuning

Usually does not require contract/spec changes unless it changes meaning.

### 14.2 Class B — Information Hierarchy
Examples:
- moving findings summary
- promoting blocked state visibility
- demoting secondary metadata

May require module-level documentation updates.

### 14.3 Class C — Interaction Behavior
Examples:
- click flow changes
- confirmation step changes
- panel response changes
- shortcut/action changes

Usually requires view-model and interaction documentation review.

### 14.4 Class D — State Communication
Examples:
- new blocked state UI
- partial trace communication
- approval-required state clarity
- running vs replay distinction

May require execution/storage/designer-facing spec sync.

### 14.5 Class E — Boundary / Architecture Sensitive
Examples:
- UI action that appears to mutate engine truth directly
- UI behavior that collapses Working Save and Commit Snapshot
- UI element that implies invalid approval semantics
- UI feature that requires new engine-owned data

Must be escalated before being treated as an ordinary UI change.

## 15. Escalation Rules

Escalation is required when a UI problem cannot be solved honestly within the UI boundary.

### 15.1 Escalate to UI Contract Review When
- a module lacks needed adapter data
- a view-model field is missing
- current module responsibilities are insufficient
- a panel boundary is unclear

### 15.2 Escalate to Storage Spec Review When
- the UI needs lifecycle information that is not clearly modeled
- Working Save / Commit Snapshot / Execution Record relationships are unclear
- UI continuity persistence collides with snapshot purity

### 15.3 Escalate to Designer Flow Spec Review When
- preview/approval states are underspecified
- ambiguity handling is unclear
- destructive edit communication is insufficient

### 15.4 Escalate to Execution/Observability Review When
- run-state visibility is inadequate
- event/timeline granularity is insufficient
- artifact provenance is too weak for the UI to explain

### 15.5 Escalate to Architecture Review When
- a proposed UI behavior implies changing ownership of truth
- a UI module needs to become engine-coupled in a nonreplaceable way
- a workaround would violate replaceability or truth boundaries

## 16. Unit Completion Criteria

A UI unit may be considered complete only when the following are satisfied.

### 16.1 Semantic Completion
- the purpose of the unit is clear
- the primary user task is visible
- the main state transitions are understandable

### 16.2 Layout Completion
- the information hierarchy is stable
- the screen/panel is scannable
- important warnings/statuses are noticeable

### 16.3 Interaction Completion
- major actions are understandable
- read-only vs intent-emitting actions are distinguishable
- dangerous/destructive actions are not ambiguous

### 16.4 Boundary Completion
- the design does not imply illegal ownership of engine truth
- the design does not collapse storage or approval boundaries
- the design does not hide blocked/confirmation-required states

### 16.5 Review Completion
- major feedback items are resolved, accepted, or explicitly deferred
- there is a stable artifact representing the final state of the unit

### 16.6 Documentation Completion
- impacted UI spec documents are updated or confirmed unchanged
- unresolved architectural dependencies are recorded

## 17. Official Close Conditions by Unit Type

### 17.1 Screen Unit Close
Requires:
- clear purpose
- stable information zones
- stable primary actions
- stable major states
- no unresolved high-severity ambiguity

### 17.2 Panel Unit Close
Requires:
- clear module responsibility
- stable field grouping
- stable status presentation
- clear editable vs read-only distinction if applicable

### 17.3 Interaction Unit Close
Requires:
- start and end state clarity
- understandable transition
- safe blocked/warning/confirmation handling
- no silent truth mutation implication

### 17.4 State Unit Close
Requires:
- the state is visually distinguishable
- its cause is understandable
- its consequence is understandable
- the next available user action is understandable

### 17.5 Flow Unit Close
Requires:
- multi-step coherence
- panel-to-panel consistency
- no lifecycle ambiguity
- no approval or storage truth confusion

## 18. Document Sync Rules

UI workflow changes must stay synchronized with the correct documents.

### 18.1 Update Architecture Package When
- module slot structure changes
- whole-shell or replaceability logic changes
- UI position relative to engine changes

### 18.2 Update View-Model Specs When
- fields change
- module responsibilities change
- state exposure changes
- interaction expectations change materially

### 18.3 Update UI State / `.nex.ui` Documents When
- UI persistence rules change
- new persistent panel/layout state is introduced
- restore behavior changes
- commit-boundary handling implications change

### 18.4 Update Workflow Protocol When
- review process changes
- fidelity levels change
- artifact expectations change
- completion criteria change
- escalation rules change

### 18.5 Update Multiple Documents When
- a change crosses workflow + module + persistence boundaries
- a UI issue exposes a missing lower-layer capability
- a new reusable pattern becomes official

## 19. Official Anti-Patterns

The following are forbidden or strongly discouraged.

### 19.1 UI-First Truth Reinterpretation
Do not change engine/storage/approval semantics just because a UI shortcut seems convenient.

### 19.2 Aesthetic-First Lock-In
Do not finalize visual polish before meaning, layout, and interaction are stable.

### 19.3 Mega-Round Review
Do not review too many screens, panels, and interactions in one round unless they are strongly coupled.

### 19.4 Ambiguous Feedback Loops
Do not accept vague feedback as sufficient closure if the screen is still visually ambiguous.

### 19.5 Prototype Authority Confusion
Do not treat draft/mock/prototype states as authoritative engine truth.

### 19.6 Silent Deferred Problems
Do not leave unresolved structural UI problems implicit.
They must be marked as:
- deferred
- rejected
- escalated
- intentionally out of scope

### 19.7 Local Hack Patterning
Do not turn one-off workaround behavior into unofficial system-wide precedent.

### 19.8 Hidden Lower-Layer Dependency
Do not disguise missing engine/adapter/spec support as a mere UI polish issue.

## 20. Recommended Default Workflow for Nexa UI

The recommended default operating flow is:

### Step 1
Select one bounded unit.

Examples:
- Graph Workspace / default draft state
- Validation Panel / blocked state
- Designer Panel / preview + approval view
- Storage Panel / draft vs snapshot comparison zone

### Step 2
Declare the exact review goal.

Examples:
- reduce confusion
- expose warning severity better
- clarify action grouping
- separate commit from run
- make blocked state understandable

### Step 3
Choose the fidelity level.

Default:
- L1 or L2 for new structure
- L3 for interaction refinement
- L5 only after stability

### Step 4
Produce the artifact.

### Step 5
Review using anchored feedback.

### Step 6
Classify change type and decide:
- revise
- accept
- defer
- escalate

### Step 7
Close the unit only if completion criteria are satisfied.

### Step 8
Sync impacted UI documents.

## 21. Default Priority Order for Early Nexa UI Work

For practical efficiency, the following order is recommended in early UI work:

1. Graph Workspace
2. Inspector Panel
3. Validation Panel
4. Execution Panel
5. Designer Panel
6. Trace / Timeline Viewer
7. Artifact Viewer
8. Storage Panel
9. Diff Viewer
10. Theme / Layout refinement

Reason:
This order follows the highest-value path from structure visibility to action safety to execution observability to lifecycle clarity.

## 22. Default Priority Order Within a Unit

Within a single UI unit, default priority is:

1. misleading meaning
2. hidden risk/blocking state
3. action ambiguity
4. information hierarchy weakness
5. interaction friction
6. density or readability issue
7. aesthetic polish

This order preserves rationality and prevents time waste.

## 23. Implementation-Handoff Readiness Criteria

A UI unit is implementation-handoff ready when:

- the purpose is stable
- the main states are covered
- primary interactions are stable
- engine truth boundaries are preserved
- affected view-model implications are known
- unresolved issues are minor or explicitly deferred
- the final prototype/mock is stable enough to implement without guessing

## 24. Versioning and Evolution

This protocol should evolve conservatively.

Minor version updates are appropriate for:
- new artifact expectations
- improved review categories
- expanded state coverage rules
- clarified escalation criteria

Major version updates are appropriate for:
- a new collaboration model
- changed fidelity ladder
- major shell/module replacement strategy changes
- fundamental changes in how UI and engine collaborate

## 25. Final Decision

Nexa UI work must be run as a bounded, artifact-based collaboration loop.

Official rule:

- define one UI unit
- set one review goal
- create an artifact
- review through anchored feedback
- revise or escalate
- close only when semantic, interactional, and boundary criteria are satisfied
- sync the correct documents

This protocol exists to maximize:
- extensibility
- efficiency
- rationality
- architectural safety
- session-to-session continuity

It is the official workflow layer for Nexa UI collaboration.

26. INTERNATIONALIZATION / LOCALIZATION REVIEW DISCIPLINE

26.1 Any new UI work that introduces user-facing text must classify that text as one of:
- UI chrome
- system message
- content-bearing text
- canonical internal value

26.2 New UI review artifacts or docs must not assume that all visible text is locale-resource text.
User/AI-authored content must remain distinguishable.

26.3 UI documentation sync is incomplete if it changes:
- user-facing strings
- locale preference behavior
- formatting behavior
- app language handling
without updating the relevant UI i18n-facing rules.

26.4 Implementation review for UI work must include a check that no new hardcoded user-facing chrome text has been added without translation-key handling.
