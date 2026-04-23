[DESIGN]
[INSPECTOR_PANEL_VIEW_MODEL_SPEC v0.2]

1. PURPOSE

This document defines the official Inspector Panel View Model
for Nexa UI.

Its purpose is to provide a stable, UI-friendly representation of
the currently selected graph object and its relevant details.

The Inspector Panel is the primary detail-and-edit-intent module
of the Nexa UI shell.

It is responsible for:

- showing what is selected
- showing editable vs read-only fields
- showing warnings and constraints
- showing related validation / execution / preview context
- collecting bounded edit intent input

It is not responsible for owning structural truth
or directly committing structural mutation.

2. POSITION IN UI ARCHITECTURE

The Inspector Panel consumes data only through the adapter/view-model boundary.

Flow:

Engine truth
→ UI Adapter / View Model Layer
→ SelectedObjectViewModel
→ Inspector Panel UI Module

The Inspector Panel must never directly read or mutate raw engine internals.

3. CORE PRINCIPLES

3.1 Inspector is a detail view, not a truth layer.
3.2 Structural truth remains engine-owned.
3.3 Inspector may present editable fields,
    but field editing is still only intent emission.
3.4 Inspector must clearly distinguish editable vs read-only.
3.5 Inspector must expose warnings, constraints, and related findings.
3.6 Inspector must remain renderable even for invalid or incomplete drafts.
3.7 Inspector must support multiple object types without collapsing semantics.

4. TOP-LEVEL VIEW MODEL

SelectedObjectViewModel
- object_type: enum(
    "node",
    "edge",
    "output",
    "group",
    "subcircuit",
    "none",
    "unknown"
  )
- object_id: optional string
- storage_role: enum("working_save", "commit_snapshot", "execution_record", "none")
- title: string
- subtitle: optional string
- description: optional string
- status_summary: ObjectStatusSummary
- editable_fields: list[EditableFieldView]
- readonly_fields: list[ReadonlyFieldView]
- warnings: list[InlineWarningView]
- constraints: list[ConstraintView]
- related_validation_findings: list[FindingRefView]
- related_execution_findings: list[FindingRefView]
- related_preview_changes: list[PreviewChangeRefView]
- related_actions: list[InspectorActionHint]
- section_order: list[string]
- empty_state_message: optional string
- explanation: optional string

5. FIELD SEMANTICS

5.1 object_type
Identifies what kind of thing is selected.
The UI must not guess this from field shape.

5.2 object_id
Stable identifier of the selected object if one exists.

5.3 storage_role
Indicates whether the current source is:
- working_save
- commit_snapshot
- execution_record
- none

This affects editability rules.

5.4 title / subtitle / description
Primary display labels for the selected object.

5.5 status_summary
Compact status projection derived from validation, execution, preview, and role context.

5.6 editable_fields / readonly_fields
Stable representation of fields the inspector may show.

5.7 warnings / constraints
User-visible risk and rule explanations.

5.8 related_* sections
Cross-links to nearby validation, execution, and preview context.

5.9 related_actions
Hints for what the user can do next from this panel.

6. OBJECT STATUS SUMMARY

ObjectStatusSummary
- overall_status: enum(
    "normal",
    "warning",
    "blocked",
    "running",
    "completed",
    "failed",
    "preview_changed",
    "readonly",
    "unknown"
  )
- validation_state: optional enum(
    "pass",
    "warning",
    "confirmation_required",
    "blocked",
    "unknown"
  )
- execution_state: optional enum(
    "idle",
    "queued",
    "running",
    "completed",
    "failed",
    "partial",
    "cancelled",
    "unknown"
  )
- preview_state: optional enum(
    "unchanged",
    "added",
    "updated",
    "removed",
    "affected",
    "none"
  )
- editability: enum(
    "editable",
    "readonly",
    "preview_only",
    "execution_locked",
    "unknown"
  )
- short_label: optional string

Rules:
- status_summary is a UI projection, not raw truth
- editability must reflect role and lifecycle boundaries
- blocked state must remain visible

7. EDITABLE FIELD VIEW

EditableFieldView
- field_key: string
- label: string
- value: any
- display_value: optional string
- editor_type: enum(
    "text",
    "textarea",
    "number",
    "toggle",
    "select",
    "multiselect",
    "json",
    "code",
    "path",
    "readonly_mirror"
  )
- required: bool
- mutable: bool
- nullable: bool
- placeholder: optional string
- help_text: optional string
- validation_hint: optional string
- allowed_values: optional list[string]
- current_source: optional string
- change_scope: optional enum("field_only", "node_level", "graph_level", "preview_only")
- dangerous: bool

Rules:
- mutable=false means UI must render as non-editable even if included here
- dangerous=true means extra confirmation UX may be needed
- current_source may show where this displayed value came from

8. READONLY FIELD VIEW

ReadonlyFieldView
- field_key: string
- label: string
- value: any
- display_value: optional string
- reason_readonly: optional string
- help_text: optional string

Purpose:
Used for fields that must be visible but not directly editable.

Examples:
- node id
- derived execution info
- commit lineage identifiers
- resolved provider metadata
- run-only status fields

9. WARNING VIEW

InlineWarningView
- warning_id: string
- severity: enum("info", "warning", "error")
- title: string
- message: string
- related_ref: optional string
- suggested_action: optional string

Rules:
- warnings must be human-readable
- warnings must not silently disappear if the draft is invalid

10. CONSTRAINT VIEW

ConstraintView
- constraint_id: string
- category: enum(
    "schema",
    "validation",
    "storage_role",
    "runtime_boundary",
    "approval_boundary",
    "execution_lock",
    "custom"
  )
- title: string
- message: string
- hard_block: bool

Purpose:
Constraints explain why some edits are limited or forbidden.

Examples:
- "Commit snapshots are read-only"
- "Execution record is not a structural editing surface"
- "Provider field cannot be changed while execution is active"

11. FINDING REFERENCE VIEW

FindingRefView
- finding_id: string
- source_type: enum("validation", "execution")
- severity: enum("info", "warning", "error", "blocked")
- short_label: string
- location_ref: optional string

Purpose:
Provides compact references to findings shown elsewhere.

12. PREVIEW CHANGE REFERENCE VIEW

PreviewChangeRefView
- change_id: string
- change_type: enum(
    "field_update",
    "node_added",
    "node_removed",
    "edge_added",
    "edge_removed",
    "output_changed",
    "metadata_changed",
    "other"
  )
- short_label: string
- destructive: bool

Purpose:
Makes pending previewed changes visible from the inspector.

13. INSPECTOR ACTION HINT

InspectorActionHint
- action_type: enum(
    "focus_validation",
    "focus_execution",
    "focus_preview",
    "open_designer_panel",
    "emit_edit_intent",
    "request_revision",
    "view_storage_state",
    "none"
  )
- label: string
- enabled: bool
- reason_disabled: optional string

Purpose:
Guides the UI on what next actions are reasonable from the selected object.

14. OBJECT-TYPE-SPECIFIC RULES

14.1 Node Selection

When object_type = "node", inspector may show:
- node metadata
- prompt/provider/plugin related fields
- binding summaries
- execution summary
- validation findings
- preview impact

Node inspector may emit bounded edit intent.

14.2 Edge Selection

When object_type = "edge", inspector may show:
- from / to refs
- edge metadata
- connection warnings
- preview state

Edge inspector may emit connect/disconnect related intent,
but not direct mutation.

14.3 Output Selection

When object_type = "output", inspector may show:
- output name
- binding source
- validation state
- preview impact

14.4 Group Selection

When object_type = "group", inspector may show:
- group metadata
- member list
- collapse/expand state
- summary findings

14.5 Subcircuit Selection

When object_type = "subcircuit", inspector may show:
- child_circuit_ref
- input_mapping summary
- output_binding summary
- runtime_policy summary
- recursion/depth safety findings if present

Rule:
Subcircuit display must not collapse parent/child truth boundaries.

15. EDITABILITY RULES BY STORAGE ROLE

15.1 working_save
- editable fields may be enabled
- invalid/incomplete drafts remain inspectable
- intent emission is allowed

15.2 commit_snapshot
- inspector is primarily readonly
- bounded review metadata actions may exist later
- structural field editing must not happen directly

15.3 execution_record
- inspector is readonly for structure
- execution-related status fields may be shown
- no structural edit intent allowed

16. EXECUTION LOCK RULES

If execution is active or the object belongs to a run-scoped context:
- structural editing may be disabled
- readonly explanation must be visible
- UI must not pretend the object is editable

Examples:
- running node
- currently active execution panel context
- execution_record-backed selection

17. PREVIEW INTEGRATION RULES

Inspector must support showing previewed changes without claiming they are committed.

Examples:
- pending provider replacement
- pending prompt change
- pending output binding change
- pending node deletion

Rules:
- previewed values must be visually distinguishable from committed values
- destructive pending edits must remain obvious
- preview-only state must not be mistaken for committed truth

18. INVALID / INCOMPLETE DRAFT SUPPORT

Inspector must remain usable even when:
- required fields are missing
- bindings are invalid
- outputs are incomplete
- validation is blocked
- preview is partial

This is required because Working Save may be invalid but still saveable.

19. MINIMUM FIRST IMPLEMENTATION

The first implementation of SelectedObjectViewModel should support:

- node selection
- edge selection
- output selection
- status summary
- editable vs readonly field split
- inline warnings
- constraint display
- related validation finding references
- related preview change references
- basic action hints

20. INSPECTOR ACTION BOUNDARY

The Inspector Panel may emit:
- bounded edit intents
- focus actions
- panel navigation hints
- designer request routing hints

The Inspector Panel must not:
- directly save structure
- directly commit changes
- directly alter validation truth
- directly alter execution truth
- bypass preview/approval flow

21. FINAL DECISION

SelectedObjectViewModel is the official UI-facing detail contract
for the currently selected object in Nexa.

It is the stable detail-and-edit-intent projection layer
for Inspector Panel UI modules.

It is not structural truth,
and it must never become a direct mutation path.

22. LOCALIZATION ALIGNMENT

22.1 Inspector text must be classified by ownership.

Localization-facing chrome/system fields:
- field labels
- section headers
- warnings and constraints when system-authored
- action hints
- empty-state text
- disabled reasons
- shell-authored explanation text

Content-bearing fields:
- selected object title/subtitle/description when sourced from user/authored/imported/AI content
- current field values
- preview snippets or execution-linked content samples

22.2 The older `string` shorthand in this document must be interpreted through the adapter contract:
- chrome/system message fields -> DisplayTextRef
- content-bearing fields -> ContentTextView

22.3 Canonical object ids, enum values, and validation codes remain language-neutral.
