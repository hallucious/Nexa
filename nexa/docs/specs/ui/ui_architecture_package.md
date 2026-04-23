[DESIGN]
[NEXA_UI_ARCHITECTURE_PACKAGE v0.2]

1. PURPOSE

This document defines the official UI architecture direction for Nexa.

The goal is to allow UI design work to proceed before full engine completion
without allowing UI decisions to distort engine architecture, storage truth,
approval truth, or execution truth.

This package fixes:

1. UI position relative to the engine
2. whole-UI replaceability
3. partial module replaceability
4. module slot system
5. module responsibilities and forbidden scope
6. engine-state vs UI-state separation
7. UI data flow model
8. current allowed UI-design scope
9. deferred UI-implementation scope
10. i18n / localization boundary

This direction matches the existing Nexa principle that UI is an upper platform layer,
not the engine core, and that UI-owned data must not redefine execution semantics.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. POSITION OF UI IN NEXA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Official structure:

Nexa Engine
→ UI Adapter / View Model Layer
→ UI Module Slots
→ Theme / Layout Layer

Meaning:

- Engine owns structural truth
- Engine owns approval truth
- Engine owns execution truth
- UI does not own those truths
- UI is a replaceable editor/view shell above the engine

Official statement:

UI may control presentation, editing ergonomics, and proposal flow.
UI must not define execution semantics, structural truth, approval truth,
or execution history truth.
Those remain engine-owned.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. CORE UI PRINCIPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3.1 UI is external to engine core
UI must be layered above the engine, not fused into it.

3.2 UI is replaceable
The system must support replacing the whole UI shell.

3.3 UI is also partially replaceable
The system must support replacing individual UI modules without requiring engine changes.

3.4 UI must be contract-bound
All UI shells and modules must operate through a shared UI contract / adapter boundary.

3.5 UI may not redefine storage lifecycle
Working Save, Commit Snapshot, and Execution Record remain engine/storage concepts,
not UI-defined concepts.

3.6 UI state is separate from engine state
UI-specific layout and interaction state must not be mixed with execution semantics.

3.7 Designer interaction remains proposal-based
Designer-originated changes must remain:
Intent → Patch → Precheck → Preview → Approval → Commit,
never direct committed mutation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. WHOLE-UI REPLACEABILITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The following must be possible:

- beginner-oriented shell
- advanced/professional shell
- internal/test shell
- future commercial shell

Condition:
All shells must consume the same engine-owned truth through the same adapter boundary.

Therefore:
UI shell replacement is allowed.
Engine truth replacement by UI is forbidden.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5. PARTIAL UI REPLACEABILITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The following must also be possible:

- replace Graph Workspace only
- replace Validation Panel only
- replace Designer Panel only
- replace Trace Viewer only
- replace Artifact Viewer only

This is allowed only if each module obeys the shared UI contract.

Therefore:
Nexa UI is not only theme-swappable.
It is module-slot-swappable.

Important distinction:

- Theme = visual skin
- Module = functional UI unit
- Shell = full UI composition

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6. OFFICIAL UI MODULE SLOT SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

6.1 Core slots v1

The initial core slot set is:

1. Graph Workspace
2. Inspector Panel
3. Validation Panel
4. Execution Panel
5. Designer Panel

Reason:
These five together cover design, inspection, validation, execution,
and Designer-AI proposal flow.

6.2 Extended slots (later)

6. Trace / Timeline Viewer
7. Artifact Viewer
8. Storage Panel
9. Diff Viewer
10. Theme / Layout Layer

6.3 Reconciliation note: historical core-slot language vs current closure scope

The core-slot taxonomy in this document is a historical UI architecture classification,
not a statement that every listed slot must be part of the same implementation batch.

In later runtime-closure planning, Storage may be treated as closure-critical
or core-equivalent for practical product-flow reasons,
even though it appears here in the extended-slot group.

Likewise, Designer remains a core architectural slot in the long-term UI module system,
even when a specific closure batch focuses on a different practical shell set.

This note exists to prevent ambiguity between:
- long-term module taxonomy
- short-term closure scope
- beginner-shell first-session surface rules

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7. MODULE RESPONSIBILITIES AND FORBIDDEN SCOPE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

7.1 Graph Workspace

Responsibilities
- show overall circuit structure
- select nodes and edges
- show grouping, collapsing, placement
- preview structural change proposals visually

Forbidden
- deciding execution order by UI rule
- confirming structural truth without validation
- creating commit snapshot directly
- mutating engine-owned structure silently

7.2 Inspector Panel

Responsibilities
- show selected object properties
- accept edit requests
- show explanations, constraints, warnings
- present editable proposal inputs

Forbidden
- directly overwriting engine-owned internal fields
- bypassing validation
- silently committing structural edits

7.3 Validation Panel

Responsibilities
- show errors, warnings, blocking findings
- show location mapping
- connect issues to repair suggestions
- display validation / precheck results

Forbidden
- silently auto-fixing and saving
- ignoring engine blocking state
- redefining validator output semantics

7.4 Execution Panel

Responsibilities
- request execution
- show current status
- show progress, recent results, stop/resume state
- display engine event stream

Forbidden
- reconstructing fake execution truth
- showing run success without engine evidence
- inventing trace/history outside engine records

7.5 Designer Panel

Responsibilities
- accept natural-language design requests
- show intent / patch / precheck / preview / approval flow
- collect approve / reject / revise actions

Forbidden
- directly mutating committed truth
- bypassing preview
- bypassing approval boundary
- silently redefining engine/runtime contracts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
8. GLOBAL UI FORBIDDEN RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

All UI slots share these prohibitions:

1. UI must not define execution semantics.
2. UI must not independently declare structural truth.
3. UI must not independently create approval truth.
4. UI must not forge execution history truth.
5. UI must not directly mutate engine-owned data.
6. UI must not collapse Working Save / Commit Snapshot / Execution Record boundaries.
7. UI must not replace validator, approval, or trace truth with local convenience logic.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
9. ENGINE-OWNED STATE VS UI-OWNED STATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

9.1 Engine-owned state

The following remain engine/storage-owned:

- circuit
- resources
- state
- validation truth
- approval truth
- execution truth
- trace truth
- storage role truth
- execution record truth

9.2 UI-owned state

The following may be UI-owned:

- node positions
- zoom level
- collapsed/expanded state
- selected object
- open/closed panels
- sorting/filtering state
- temporary visual emphasis
- workspace layout presets

This matches the rule that UI data may exist, but must not redefine execution semantics.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
10. UI DATA FLOW MODEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Official data flow:

Engine
→ UI Adapter / View Model Store
  → Graph Workspace
  → Inspector Panel
  → Validation Panel
  → Execution Panel
  → Designer Panel

Rules:

10.1 UI modules do not directly bind to raw engine mutation paths
10.2 UI modules communicate through shared adapter/view-model boundaries
10.3 edit requests become edit intent or proposal input, not direct commit
10.4 execution display must come from engine events and records
10.5 Designer output must go through proposal pipeline

Example flows:

A. Graph → Inspector
- graph selects node
- inspector reads selection model
- inspector emits edit intent

B. Inspector → Validation
- edit request sent
- engine/validator evaluates
- validation panel shows result

C. Execution → Graph / Validation
- execution event stream arrives
- execution panel shows progress
- graph highlights active node
- validation shows runtime warnings/failures

D. Designer → Graph / Validation / Inspector
- designer request produces intent/patch/precheck/preview
- graph shows structure preview
- validation shows risk/blocking findings
- inspector shows affected details

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
11. MINIMUM UI CONTRACT DIRECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

All shells and modules should be able to rely on a common UI contract.

Minimum direction:

- read_graph_view_model()
- read_selected_object()
- emit_edit_intent()
- read_validation_report()
- read_execution_events()
- read_designer_preview()
- emit_approval_action()

Meaning:
UI modules do not directly “save truth”.
They read truth and emit intents/actions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
12. CURRENTLY ALLOWED UI WORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The following UI work is allowed now, even before full engine completion:

- UI architecture design
- module-slot design
- module data flow design
- wireframes
- information hierarchy
- beginner/advanced shell split
- engine-state vs UI-state boundary definition
- event display design
- proposal-flow UX design

Reason:
These do not force premature engine implementation,
as long as they do not redefine engine truth.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
13. CURRENTLY DISALLOWED / DEFERRED UI WORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The following should be deferred:

- full frontend implementation tightly bound to unfinished engine APIs
- UI-driven savefile meaning changes
- UI-driven approval boundary changes
- UI-driven trace/history reinterpretation
- UI-first engine contract freezing
- detailed production interaction coding that assumes final engine shape

In other words:
UI architecture work is allowed now.
UI implementation that constrains engine evolution is not.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
14. RECOMMENDED LOW-FIDELITY SCREEN STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Recommended starter layout:

Top Bar
- file / mode / run / save / status

Left Panel
- graph tree / module navigation

Center
- graph workspace

Right Panel
- inspector
- designer

Bottom Tabs
- validation
- execution
- preview

Purpose:
This is not a final implementation mandate.
It is a low-fidelity structural arrangement for design thinking only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
15. FINAL DECISION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Nexa UI shall be designed as:

- a replaceable shell above the engine
- internally modular and partially replaceable
- contract-bound through adapter/view-model boundaries
- separated from engine-owned truth
- allowed to proceed at architecture/UX/wireframe level now
- not allowed to prematurely lock unfinished engine implementation

One-sentence summary:

Nexa UI is a modular, replaceable editor/view shell above an engine that remains the sole owner of structural, approval, and execution truth.

16. INTERNATIONALIZATION / LOCALIZATION ALIGNMENT

16.1 UI architecture must remain i18n-ready.
The absence of early i18n structure is now treated as an avoidable inefficiency,
not as a neutral omission.

16.2 UI chrome, system message text, content-bearing text,
and canonical engine values must be kept separate.

16.3 App language belongs to UI-owned state.
AI response language is a separate policy concern and must not be fused into
Theme / Layout or shell chrome assumptions.

16.4 UI modules must be designed to tolerate text expansion and locale-aware formatting.

16.5 Canonical engine/storage ids and enums remain language-neutral.
Localization happens only at presentation time.

16.6 This package must be read together with:
- `docs/specs/ui/ui_internationalization_localization_spec.md`
- `docs/specs/ui/ui_adapter_view_model_contract.md`
- `docs/specs/ui/ui_state_ownership_and_persistence_spec.md`
