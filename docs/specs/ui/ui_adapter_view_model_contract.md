[DESIGN]
[UI_ADAPTER_VIEW_MODEL_CONTRACT v0.1]

1. PURPOSE

This document defines the official adapter / view-model boundary
between the Nexa engine and all UI shells/modules.

Its purpose is to ensure that:

1. UI reads engine-owned truth through a stable contract
2. UI emits intents/actions instead of mutating truth directly
3. whole-UI replacement remains possible
4. partial module replacement remains possible
5. engine evolution and UI evolution remain decoupled

This contract exists because the official UI direction for Nexa is:

Nexa Engine
→ UI Adapter / View Model Layer
→ UI Module Slots
→ Theme / Layout Layer

UI is not allowed to own structural truth, approval truth,
or execution truth.
Those remain engine-owned.

2. CORE PRINCIPLES

2.1 Adapter is the only official boundary between engine and UI.
2.2 UI must not directly mutate raw engine data structures.
2.3 Adapter output must be UI-friendly, not engine-internal.
2.4 Adapter input from UI must be intent/action based.
2.5 Different UI shells may reuse the same adapter contract.
2.6 Different UI modules may consume only the slices they need.
2.7 Adapter must preserve engine/storage lifecycle boundaries.

3. WHAT THE ADAPTER MAY DO

The adapter layer MAY:

- reshape engine models into UI-readable view models
- aggregate validation findings into panel-friendly structures
- aggregate execution events into timeline-friendly structures
- convert Designer pipeline objects into preview-friendly structures
- expose selection-safe summaries of storage artifacts
- provide stable read APIs for modules
- accept UI actions and convert them into engine-facing intents

4. WHAT THE ADAPTER MUST NOT DO

The adapter layer MUST NOT:

- directly commit structural mutations
- fabricate approval truth
- fabricate execution history truth
- reinterpret blocked proposals as valid
- silently repair invalid structures
- collapse Working Save / Commit Snapshot / Execution Record boundaries
- hide destructive changes from the UI
- bypass validator/precheck/preview/approval flow

5. ENGINE-OWNED TRUTH DOMAINS

The adapter reads from engine-owned truth domains.

These remain engine-owned:

- circuit structure truth
- resources truth
- validation truth
- approval truth
- execution truth
- trace/history truth
- storage role truth
- commit lineage truth

The adapter may expose them in transformed UI form,
but may not redefine them.

6. UI-OWNED STATE DOMAINS

The adapter may also work with UI-owned state.

These may remain UI-owned:

- selected object
- current panel/tab
- node positions
- zoom level
- collapsed/expanded state
- local filtering/sorting
- temporary highlights
- layout presets

Rule:
UI-owned state must not change execution semantics.

7. CONTRACT SHAPE

The contract has two directions:

A. READ SIDE
Engine → Adapter → UI View Models

B. WRITE SIDE
UI Action / Intent → Adapter → Engine Intent / Request

This means the adapter is not a repository of truth.
It is a transformation and routing boundary.

8. READ-SIDE CONTRACT

8.1 Graph Workspace View Model

read_graph_view_model() returns GraphWorkspaceViewModel

GraphWorkspaceViewModel
- graph_id: string
- nodes: list[GraphNodeView]
- edges: list[GraphEdgeView]
- selected_node_ids: list[string]
- selected_edge_ids: list[string]
- groups: list[GraphGroupView]
- graph_status: enum("draft", "review_ready", "approved", "invalid", "executed")
- layout_hints: optional dict

GraphNodeView
- node_id: string
- label: string
- kind: string
- status: enum("normal", "warning", "error", "running", "completed", "blocked")
- input_summary: optional string
- output_summary: optional string
- validation_badge_count: int
- execution_badge_count: int
- preview_change_state: enum("unchanged", "added", "updated", "removed", "affected")

GraphEdgeView
- edge_id: string
- from_node_id: string
- to_node_id: string
- status: enum("normal", "warning", "error", "preview_added", "preview_removed")

GraphGroupView
- group_id: string
- label: string
- member_node_ids: list[string]
- collapsed: bool

8.2 Inspector View Model

read_selected_object() returns SelectedObjectViewModel

SelectedObjectViewModel
- object_type: enum("node", "edge", "output", "group", "none")
- object_id: optional string
- title: string
- description: optional string
- editable_fields: list[EditableFieldView]
- warnings: list[InlineWarningView]
- related_validation_findings: list[string]
- related_execution_findings: list[string]
- related_preview_changes: list[string]

EditableFieldView
- field_key: string
- label: string
- value: any
- editor_type: enum("text", "textarea", "number", "toggle", "select", "json", "readonly")
- required: bool
- mutable: bool
- help_text: optional string

8.3 Validation Panel View Model

read_validation_report() returns ValidationPanelViewModel

ValidationPanelViewModel
- overall_status: enum("pass", "pass_with_warnings", "confirmation_required", "blocked")
- blocking_count: int
- warning_count: int
- confirmation_count: int
- findings: list[ValidationFindingView]

ValidationFindingView
- finding_id: string
- severity: enum("blocking", "warning", "confirmation_required")
- code: string
- title: string
- message: string
- location_ref: optional string
- suggested_action: optional string

8.4 Execution Panel View Model

read_execution_view_model() returns ExecutionPanelViewModel

ExecutionPanelViewModel
- execution_status: enum("idle", "queued", "running", "completed", "failed", "partial", "cancelled")
- current_node_id: optional string
- started_at: optional string
- finished_at: optional string
- progress_percent: optional float
- summary: optional string
- latest_events: list[ExecutionEventView]
- latest_outputs: list[OutputSummaryView]

ExecutionEventView
- event_id: string
- event_type: string
- timestamp: string
- node_id: optional string
- short_message: string

OutputSummaryView
- output_name: string
- value_preview: string

8.5 Designer Panel View Model

read_designer_preview() returns DesignerPanelViewModel

DesignerPanelViewModel
- current_request_text: optional string
- intent_summary: optional string
- patch_summary: optional string
- precheck_status: optional string
- preview_summary: optional string
- requires_confirmation: bool
- pending_questions: list[string]
- preview_ref: optional string

8.6 Storage View Model

read_storage_view_model() returns StorageViewModel

StorageViewModel
- current_storage_role: enum("working_save", "commit_snapshot", "execution_record", "none")
- working_save_id: optional string
- commit_id: optional string
- run_id: optional string
- dirty_state: bool
- review_state: enum("draft", "review_ready", "approved", "executed", "unknown")
- latest_saved_at: optional string

9. WRITE-SIDE CONTRACT

UI never sends direct mutations.
UI sends actions or intents.

9.1 Selection Action

emit_selection_action(action)

SelectionAction
- action_type: enum("select_node", "select_edge", "clear_selection", "focus_node", "focus_finding")
- target_ref: optional string

9.2 Layout Action

emit_layout_action(action)

LayoutAction
- action_type: enum("move_node", "set_zoom", "collapse_group", "expand_group", "set_panel_layout")
- payload: dict

Rule:
layout actions affect UI state only.

9.3 Edit Intent

emit_edit_intent(intent)

EditIntent
- intent_id: string
- target_ref: string
- change_type: enum("set_field", "connect_nodes", "disconnect_nodes", "create_node", "delete_node", "rename", "set_output_binding")
- payload: dict
- source: enum("graph_workspace", "inspector", "designer_panel")

Rule:
EditIntent is not a commit.
It must go through validation/precheck flow where applicable.

9.4 Execution Action

emit_execution_action(action)

ExecutionAction
- action_type: enum("run", "cancel", "pause", "resume", "replay")
- target_ref: optional string
- payload: optional dict

Rule:
Execution requests may only run against engine-allowed artifacts/boundaries.

9.5 Designer Request Action

emit_designer_request(action)

DesignerRequestAction
- action_type: enum("submit_request", "request_revision", "approve_preview", "reject_preview", "choose_interpretation")
- request_text: optional string
- preview_ref: optional string
- selected_option: optional string
- notes: optional string

Rule:
Designer requests must continue to use:
Intent → Patch → Precheck → Preview → Approval → Commit

10. MODULE-SPECIFIC CONSUMPTION RULES

10.1 Graph Workspace
Consumes:
- GraphWorkspaceViewModel
- selection actions
- layout actions
- edit intents (limited)

Must not:
- directly save
- directly commit
- directly bypass validation

10.2 Inspector Panel
Consumes:
- SelectedObjectViewModel
- validation slice
- preview slice

May emit:
- edit intents

Must not:
- write raw node objects directly

10.3 Validation Panel
Consumes:
- ValidationPanelViewModel

May emit:
- focus_finding selection action

Must not:
- auto-fix and save silently

10.4 Execution Panel
Consumes:
- ExecutionPanelViewModel

May emit:
- execution actions

Must not:
- fabricate runtime status

10.5 Designer Panel
Consumes:
- DesignerPanelViewModel
- preview slice
- validation slice

May emit:
- designer request actions

Must not:
- cross commit boundary without approval

11. ADAPTER STABILITY RULES

11.1 UI modules must depend on adapter contracts, not raw engine internals.
11.2 Engine internal refactors should preserve adapter compatibility where possible.
11.3 Breaking adapter contract changes must be versioned explicitly.
11.4 New UI modules should be added by extending adapter surfaces, not by bypassing them.
11.5 Adapter should prefer additive evolution over destructive field churn.

12. ERROR HANDLING

If engine-side data is incomplete or invalid:

- adapter should still return partial view models when possible
- adapter must expose blocked/incomplete state explicitly
- adapter must not pretend the model is valid
- adapter may include `data_incomplete = true` style metadata when needed

This is especially important because Working Save may be incomplete or invalid while still being saveable.

13. RELATIONSHIP TO STORAGE LIFECYCLE

Adapter must preserve storage distinctions:

13.1 Working Save
- editable current artifact
- may be incomplete/invalid

13.2 Commit Snapshot
- approved structural anchor
- not draft clutter

13.3 Execution Record
- run/history artifact
- not editable structural truth

UI may show all three,
but adapter must not blur them into a single ambiguous model.

14. MINIMUM FIRST IMPLEMENTATION

The first adapter implementation should support:

- graph workspace read model
- selected object read model
- validation panel read model
- execution panel read model
- designer preview read model
- storage state read model
- selection action
- layout action
- edit intent
- execution action
- designer request action

15. FINAL DECISION

Nexa UI must not talk to engine truth directly.

The official boundary is:

Engine truth
→ Adapter / View Model Contract
→ UI modules

and

UI actions/intents
→ Adapter
→ Engine-side intent/request handling

This preserves:
- engine sovereignty over truth
- UI replaceability
- module replaceability
- proposal-safe Designer flow
- storage lifecycle clarity