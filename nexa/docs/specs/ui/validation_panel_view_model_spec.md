[DESIGN]
[VALIDATION_PANEL_VIEW_MODEL_SPEC v0.2]

1. PURPOSE

This document defines the official Validation Panel View Model
for Nexa UI.

Its purpose is to provide a stable, UI-friendly representation of
validation findings, precheck findings, structural blocking issues,
warnings, and confirmation-required risks.

The Validation Panel is the primary error/risk/explainability module
of the Nexa UI shell.

It is responsible for:

- showing whether the current target is pass / warning / blocked
- grouping findings by severity and category
- mapping findings to graph/object locations
- exposing suggested next actions
- showing why a commit or execution is blocked
- showing confirmation-required risks separately from hard blocking errors

It is not responsible for silently repairing structure,
redefining validator output,
or bypassing approval boundaries.

2. POSITION IN UI ARCHITECTURE

The Validation Panel consumes data only through the adapter/view-model boundary.

Flow:

Engine truth
→ UI Adapter / View Model Layer
→ ValidationPanelViewModel
→ Validation Panel UI Module

The Validation Panel must never directly read or mutate raw engine internals.

3. CORE PRINCIPLES

3.1 Validation Panel is a finding/explanation layer, not a truth layer.
3.2 Validation truth remains engine-owned.
3.3 Validation findings must remain visible even when the draft is invalid.
3.4 Blocking findings, warnings, and confirmation-required findings must be distinct.
3.5 The panel must support both current-state validation and proposal/precheck validation.
3.6 The panel must remain renderable for incomplete drafts.
3.7 The panel must help the user understand what to do next without silently fixing anything.

4. TOP-LEVEL VIEW MODEL

ValidationPanelViewModel
- source_mode: enum(
    "working_save_validation",
    "commit_snapshot_validation",
    "designer_precheck",
    "execution_guard",
    "unknown"
  )
- storage_role: enum("working_save", "commit_snapshot", "execution_record", "none")
- overall_status: enum(
    "pass",
    "pass_with_warnings",
    "confirmation_required",
    "blocked",
    "unknown"
  )
- summary: ValidationSummaryView
- blocking_findings: list[ValidationFindingView]
- warning_findings: list[ValidationFindingView]
- confirmation_findings: list[ValidationFindingView]
- informational_findings: list[ValidationFindingView]
- grouped_sections: list[ValidationGroupView]
- related_targets: list[ValidationTargetSummary]
- suggested_actions: list[ValidationActionHint]
- filter_state: ValidationFilterState
- explanation: optional string

5. FIELD SEMANTICS

5.1 source_mode
Indicates what kind of validation surface is being shown.

Examples:
- working_save_validation
- commit_snapshot_validation
- designer_precheck
- execution_guard

The UI must not guess this from findings alone.

5.2 storage_role
Indicates which storage layer the findings relate to.

5.3 overall_status
Top-level validation state.

Semantics:
- pass: no significant findings
- pass_with_warnings: warnings exist, but no blocking issues
- confirmation_required: no blocking issues, but commit/approval should require explicit acknowledgment
- blocked: hard blocking issues remain
- unknown: insufficient data to determine safely

5.4 summary
Compact counts and top-level interpretation.

5.5 finding lists
Stable per-severity slices for display and filtering.

5.6 grouped_sections
Alternative grouped representation for category-oriented UIs.

5.7 related_targets
High-level summary of affected graph objects or sections.

5.8 suggested_actions
UI-facing next-step hints.

5.9 filter_state
UI filter defaults projected into the model when needed.

6. VALIDATION SUMMARY VIEW

ValidationSummaryView
- blocking_count: int
- warning_count: int
- confirmation_count: int
- info_count: int
- affected_node_count: int
- affected_edge_count: int
- affected_output_count: int
- affected_group_count: int
- top_issue_label: optional string
- can_commit: bool
- can_execute: bool
- requires_user_confirmation: bool

Rules:
- can_commit must reflect engine-owned validation state
- can_execute must not be guessed by UI convenience logic
- requires_user_confirmation must remain explicit

7. VALIDATION FINDING VIEW

ValidationFindingView
- finding_id: string
- severity: enum("blocking", "warning", "confirmation_required", "info")
- category: enum(
    "schema",
    "structure",
    "dependency",
    "input_output",
    "provider",
    "plugin",
    "storage_role",
    "approval_boundary",
    "execution_guard",
    "safety",
    "cost",
    "ambiguity",
    "custom"
  )
- code: string
- title: string
- message: string
- short_label: optional string
- location_ref: optional string
- target_type: optional enum(
    "node",
    "edge",
    "output",
    "group",
    "graph",
    "storage",
    "designer_proposal",
    "unknown"
  )
- target_id: optional string
- source_ref: optional string
- suggested_action: optional string
- docs_ref: optional string
- user_confirmation_allowed: bool
- auto_resolvable: bool
- destructive_risk: bool

Rules:
- code must be stable enough for engine/UI linking
- destructive_risk must remain visible
- auto_resolvable does not grant silent auto-fix permission
- user_confirmation_allowed must not downgrade blocking issues by itself

8. VALIDATION GROUP VIEW

ValidationGroupView
- group_id: string
- group_label: string
- group_type: enum(
    "severity",
    "category",
    "target",
    "proposal_scope",
    "custom"
  )
- findings: list[ValidationFindingView]
- count: int
- collapsed_by_default: bool

Purpose:
Supports grouped rendering such as:
- all blocking issues
- all provider issues
- all findings touching node X

9. VALIDATION TARGET SUMMARY

ValidationTargetSummary
- target_type: enum("node", "edge", "output", "group", "graph", "storage", "unknown")
- target_id: optional string
- title: string
- blocking_count: int
- warning_count: int
- confirmation_count: int
- info_count: int

Purpose:
Supports side lists such as:
- “3 issues on node compare_models”
- “1 blocking issue on output final_answer”

10. VALIDATION ACTION HINT

ValidationActionHint
- action_type: enum(
    "focus_target",
    "open_inspector",
    "open_designer_panel",
    "show_preview",
    "request_revision",
    "acknowledge_confirmation",
    "view_docs",
    "none"
  )
- label: string
- enabled: bool
- reason_disabled: optional string
- target_ref: optional string

Purpose:
Helps the UI guide the user toward reasonable next steps.

11. VALIDATION FILTER STATE

ValidationFilterState
- show_blocking: bool
- show_warnings: bool
- show_confirmations: bool
- show_info: bool
- group_by: enum("severity", "category", "target", "none")
- search_query: optional string

Purpose:
Optional projected filter defaults for richer UIs.

12. FINDING LOCATION RULES

Every finding should expose location information when possible.

Preferred location_ref patterns:
- node:<node_id>
- edge:<edge_id>
- output:<output_name>
- group:<group_id>
- graph
- storage
- designer_preview:<preview_id>

Rules:
- the panel must not invent fake locations
- if exact location is unknown, location_ref may be omitted
- target_type/target_id should remain consistent with location_ref when present

13. STATUS DISTINCTION RULES

The panel must clearly separate:

13.1 blocking
Hard stop.
Examples:
- invalid structural dependency
- missing required output binding
- unresolved subcircuit reference
- commit snapshot violation

13.2 warning
Non-blocking risk.
Examples:
- weak output mapping
- missing optional metadata
- low-confidence provider choice

13.3 confirmation_required
User decision required before commit/approval.
Examples:
- destructive edit preview
- risky provider replacement
- broad patch with unclear tradeoff

13.4 info
Helpful but non-urgent findings.

Rule:
confirmation_required must not be visually merged into warnings.

14. DESIGNER PRECHECK INTEGRATION RULES

When source_mode = "designer_precheck",
the panel must support proposal-oriented findings.

Examples:
- ambiguity in target scope
- destructive change requires confirmation
- provider restriction conflict
- output behavior may change
- cost increase expected

Rules:
- these findings are about proposed future state, not only current state
- proposal findings must remain distinguishable from current structural findings
- the panel must not pretend previewed changes are already committed

15. STORAGE ROLE RULES

15.1 working_save
- permissive validation surface
- incomplete/invalid drafts still render
- findings may explain why execution or commit is currently blocked

15.2 commit_snapshot
- stricter validation surface
- unresolved blocking issues should not normally exist
- if shown, they represent invalid loaded state or migration failure

15.3 execution_record
- structural validation is mostly readonly/history-oriented
- execution-guard or replay-related findings may appear
- no structural edit suggestions should imply direct mutation

16. EXECUTION GUARD RULES

Some findings may come from execution gating rather than structural schema.

Examples:
- execution locked while run is active
- provider not resolvable in current environment
- required plugin unavailable
- replay target missing artifact reference

Rules:
- execution guard findings must be visible
- they must not be mislabeled as structural schema errors

17. INVALID / INCOMPLETE DRAFT SUPPORT

Validation Panel must remain usable even when:
- entry is missing
- outputs are incomplete
- node bindings are broken
- preview is partial
- draft is blocked

This is required because Working Save may be invalid but still saveable.

18. MINIMUM FIRST IMPLEMENTATION

The first implementation of ValidationPanelViewModel should support:

- overall_status
- summary counts
- blocking/warning/confirmation/info separation
- stable finding codes
- location references
- target summaries
- suggested actions
- working_save validation
- designer precheck validation

19. PANEL ACTION BOUNDARY

The Validation Panel may emit:
- focus actions
- open-inspector actions
- open-designer actions
- preview navigation hints
- explicit acknowledgment actions for confirmation-required findings

The Validation Panel must not:
- silently repair the draft
- directly save structure
- directly commit changes
- directly override validator results
- hide blocking state for convenience

20. FINAL DECISION

ValidationPanelViewModel is the official UI-facing contract
for presenting validation truth, precheck findings,
and commit/execution blocking reasons in Nexa.

It is the stable finding-and-explanation projection layer
for Validation Panel UI modules.

It is not the validator itself,
and it must never become an auto-fix mutation path.

21. LOCALIZATION ALIGNMENT

21.1 Validation presentation must separate stable findings from localized display.

Stable internal values:
- finding ids
- category ids
- severity ids
- reason codes
- target refs

Localized UI-facing values:
- finding titles
- explanatory messages
- suggestion labels
- confirmation-required prompts
- blocked/warning status labels

21.2 Validation messages must preferably be rendered from stable message ids/reason codes,
not hardcoded English strings.

21.3 Compared object names or user-authored target labels remain content-bearing text,
not locale-resource strings.
