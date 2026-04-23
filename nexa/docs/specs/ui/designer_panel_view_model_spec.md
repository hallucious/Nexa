[DESIGN]
[DESIGNER_PANEL_VIEW_MODEL_SPEC v0.2]

1. PURPOSE

This document defines the official Designer Panel View Model
for Nexa UI.

Its purpose is to provide a stable, UI-friendly representation of:

- user design request input
- normalized design intent
- patch planning state
- validator precheck state
- preview state
- approval state
- revision / retry state
- bounded Designer actions

The Designer Panel is the primary proposal-and-approval-flow module
of the Nexa UI shell.

It is responsible for:

- accepting natural-language design requests
- showing how the request was interpreted
- showing what patch/proposal is being prepared
- showing what the validator/precheck found
- showing what preview is ready
- collecting approve / reject / revise / choose-interpretation actions

It is not responsible for directly mutating committed structural truth.

2. POSITION IN UI ARCHITECTURE

The Designer Panel consumes data only through the adapter/view-model boundary.

Flow:

Engine truth
→ UI Adapter / View Model Layer
→ DesignerPanelViewModel
→ Designer Panel UI Module

The Designer Panel must never directly read or mutate raw engine internals.

3. CORE PRINCIPLES

3.1 Designer Panel is a proposal-flow layer, not a truth layer.
3.2 Structural truth remains engine-owned.
3.3 Designer output must remain proposal-based.
3.4 Ambiguity, destructive change, and blocking issues must remain visible.
3.5 Preview must be shown before commit/approval.
3.6 Approval state must remain explicit.
3.7 Revision loops must not silently overwrite prior user intent.

4. TOP-LEVEL VIEW MODEL

DesignerPanelViewModel
- session_mode: enum(
    "create_circuit",
    "modify_circuit",
    "repair_circuit",
    "optimize_circuit",
    "explain_circuit",
    "analyze_circuit",
    "idle",
    "unknown"
  )
- storage_role: enum("working_save", "commit_snapshot", "execution_record", "none")
- request_state: DesignerRequestStateView
- intent_state: DesignerIntentStateView
- patch_state: DesignerPatchStateView
- precheck_state: DesignerPrecheckStateView
- preview_state: DesignerPreviewStateView
- approval_state: DesignerApprovalStateView
- revision_state: DesignerRevisionStateView
- suggested_actions: list[DesignerActionHint]
- related_targets: list[DesignerTargetRefView]
- explanation: optional string

5. FIELD SEMANTICS

5.1 session_mode
Indicates what kind of design activity is active.

Examples:
- create_circuit
- modify_circuit
- repair_circuit
- optimize_circuit
- explain_circuit
- analyze_circuit

5.2 storage_role
Indicates the storage layer currently being targeted/viewed.

5.3 request_state
Current user request text and request-entry status.

5.4 intent_state
How the request was normalized/interpreted.

5.5 patch_state
Structured patch/proposal planning status.

5.6 precheck_state
Validator/precheck outcome for the proposed future state.

5.7 preview_state
What preview is ready and what change scope it implies.

5.8 approval_state
Whether approval is required, pending, granted, or rejected.

5.9 revision_state
Revision/retry loop state.

6. DESIGNER REQUEST STATE VIEW

DesignerRequestStateView
- current_request_text: optional string
- request_status: enum(
    "empty",
    "drafting",
    "submitted",
    "interpreting",
    "ready",
    "failed",
    "unknown"
  )
- last_submitted_at: optional string
- input_placeholder: optional string
- can_submit: bool
- submit_reason_disabled: optional string

Purpose:
Represents the user-facing entry state for new Designer requests.

7. DESIGNER INTENT STATE VIEW

DesignerIntentStateView
- intent_id: optional string
- category: optional enum(
    "CREATE_CIRCUIT",
    "MODIFY_CIRCUIT",
    "EXPLAIN_CIRCUIT",
    "ANALYZE_CIRCUIT",
    "REPAIR_CIRCUIT",
    "OPTIMIZE_CIRCUIT",
    "unknown"
  )
- target_scope_summary: optional string
- objective_summary: optional string
- constraints_summary: optional string
- assumption_count: int
- ambiguity_count: int
- risk_flag_count: int
- confidence: optional float
- explanation: optional string

Rules:
- intent state reflects interpreted proposal intent, not committed truth
- ambiguity_count must remain visible
- confidence must not be presented as certainty

8. DESIGNER PATCH STATE VIEW

DesignerPatchStateView
- patch_id: optional string
- patch_mode: optional enum(
    "create_draft",
    "modify_existing",
    "repair_existing",
    "optimize_existing",
    "analysis_only",
    "unknown"
  )
- summary: optional string
- operation_count: int
- scope_level: optional enum("minimal", "bounded", "broad", "unknown")
- touch_mode: optional enum(
    "read_only",
    "append_only",
    "structural_edit",
    "destructive_edit",
    "unknown"
  )
- touched_node_count: int
- touched_edge_count: int
- touched_output_count: int
- destructive_change_present: bool
- reversibility_summary: optional string

Rules:
- destructive_change_present must remain visible
- analysis_only must never be shown as a commit-ready patch
- patch state must remain separate from preview state

9. DESIGNER PRECHECK STATE VIEW

DesignerPrecheckStateView
- precheck_id: optional string
- overall_status: enum(
    "not_run",
    "pass",
    "pass_with_warnings",
    "confirmation_required",
    "blocked",
    "failed",
    "unknown"
  )
- blocking_count: int
- warning_count: int
- confirmation_count: int
- top_issue_label: optional string
- can_proceed_to_preview: bool
- can_proceed_to_approval: bool
- recommended_next_step: optional string

Rules:
- blocked must remain distinct from failed
- can_proceed_to_approval must remain false when blocking findings exist
- confirmation_required must not be collapsed into pass_with_warnings

10. DESIGNER PREVIEW STATE VIEW

DesignerPreviewStateView
- preview_id: optional string
- preview_status: enum(
    "not_ready",
    "building",
    "ready",
    "stale",
    "failed",
    "unknown"
  )
- one_sentence_summary: optional string
- proposal_type: optional enum("create", "modify", "repair", "optimize", "analyze", "unknown")
- change_scope: optional enum("minimal", "bounded", "broad", "unknown")
- touched_node_count: int
- touched_edge_count: int
- touched_output_count: int
- risk_summary: optional string
- cost_summary: optional string
- confirmation_required: bool
- graph_preview_available: bool

Rules:
- ready preview must not be treated as committed structure
- stale preview must remain visibly stale after revision/input changes
- graph_preview_available only indicates preview support, not approval

11. DESIGNER APPROVAL STATE VIEW

DesignerApprovalStateView
- approval_required: bool
- approval_status: enum(
    "not_required",
    "pending",
    "approved",
    "rejected",
    "expired",
    "unknown"
  )
- approval_reason: optional string
- approved_at: optional string
- rejected_at: optional string
- can_approve: bool
- can_reject: bool
- can_request_revision: bool

Rules:
- approval_status must remain explicit
- approval must not be inferred from preview readiness
- rejected state must remain visible until superseded by a later proposal

12. DESIGNER REVISION STATE VIEW

DesignerRevisionStateView
- revision_count: int
- last_revision_reason: optional string
- current_branch_label: optional string
- has_pending_questions: bool
- pending_question_count: int
- last_user_choice_summary: optional string
- can_retry_interpretation: bool

Purpose:
Represents iterative proposal refinement state.

13. DESIGNER ACTION HINT

DesignerActionHint
- action_type: enum(
    "submit_request",
    "request_revision",
    "approve_preview",
    "reject_preview",
    "choose_interpretation",
    "show_precheck",
    "show_preview",
    "focus_graph_changes",
    "focus_validation",
    "clear_request",
    "none"
  )
- label: string
- enabled: bool
- reason_disabled: optional string
- target_ref: optional string

Purpose:
Guides the UI toward valid next steps in the Designer flow.

14. DESIGNER TARGET REFERENCE VIEW

DesignerTargetRefView
- target_type: enum(
    "graph",
    "node",
    "edge",
    "output",
    "subgraph",
    "storage",
    "unknown"
  )
- target_id: optional string
- title: string
- change_summary: optional string

Purpose:
Gives the Designer Panel compact references to affected objects.

15. FLOW STAGE RULES

The Designer Panel must represent the canonical Designer flow:

User Request
→ Intent
→ Patch
→ Precheck
→ Preview
→ Approval
→ Commit

Rules:
- commit is downstream and not performed by the panel itself
- if a stage fails, the failure must remain visible
- skipped stages must be explicit, not silently omitted

16. AMBIGUITY RULES

If a request is materially ambiguous:
- ambiguity_count must be > 0
- has_pending_questions may be true
- choose_interpretation or request_revision actions may be enabled
- approval should not be silently enabled as if the proposal were unambiguous

17. DESTRUCTIVE CHANGE RULES

If patch_state.touch_mode = destructive_edit
or preview_state.confirmation_required = true:
- destructive change must remain visible
- approval_required must be true
- the panel must not present the proposal as harmless

18. STORAGE ROLE RULES

18.1 working_save
- primary target for Designer proposal flow
- create / modify / repair / optimize may be active
- approval/commit flows may be relevant

18.2 commit_snapshot
- generally readonly structural anchor
- explain/analyze may be active
- direct design mutation flow should not imply direct commit mutation

18.3 execution_record
- primarily readonly history surface
- explain/analyze of past run context may exist
- create/modify patch flow against execution history must not be implied

19. INVALID / INCOMPLETE DRAFT SUPPORT

Designer Panel must remain usable even when:
- current working save is invalid
- validation is blocked
- preview cannot yet be built
- request is ambiguous
- patch touches incomplete graph structure

This is required because Working Save may be invalid but still saveable.

20. DESIGNER PANEL ACTION BOUNDARY

The Designer Panel may emit:
- submit request actions
- request revision actions
- approve/reject actions
- choose interpretation actions
- navigation hints to graph/validation/preview surfaces

The Designer Panel must not:
- directly mutate committed truth
- directly save structural edits
- silently skip precheck
- silently skip preview
- silently cross approval boundary

21. MINIMUM FIRST IMPLEMENTATION

The first implementation of DesignerPanelViewModel should support:

- request entry state
- normalized intent summary
- patch summary
- precheck status summary
- preview readiness state
- approval state
- revision count/state
- suggested actions
- create/modify/repair/optimize modes

22. FINAL DECISION

DesignerPanelViewModel is the official UI-facing contract
for presenting Designer request interpretation,
proposal planning, precheck, preview, approval,
and revision flow in Nexa.

It is the stable proposal-and-approval-flow projection layer
for Designer Panel UI modules.

It is not the Designer engine itself,
and it must never become a direct structural mutation path.

23. LOCALIZATION ALIGNMENT

23.1 Designer Panel has both chrome text and content text.

Localization-facing chrome/system fields:
- input placeholder
- submit / preview / approve / revise action labels
- disabled reasons
- precheck/approval prompts
- shell-authored revision guidance

Content-bearing fields:
- current user request text
- normalized intent explanations generated as content
- preview summaries generated by AI/design pipeline
- patch/precheck content excerpts

23.2 App language and AI response language must remain separate.
Changing panel chrome language must not silently rewrite generated Designer content language.

23.3 The older `string` shorthand in this spec must be read through the adapter contract:
chrome/system fields -> DisplayTextRef
content-bearing fields -> ContentTextView

19. GOVERNANCE DECISION BOUNDARY

The Designer Panel is a READ-ONLY projection of engine-generated Designer governance state.

The following responsibilities MUST remain engine-owned and MUST NOT be implemented in UI code:

1. Preview generation
   - Engine builds preview through `src/designer/preview_builder.py`
   - UI reads preview state through `DesignerPreviewStateView`
   - UI MUST NOT generate `CircuitDraftPreview` locally

2. Validation precheck execution
   - Engine computes `ValidationPrecheck`
   - UI reads precheck state through `DesignerPrecheckStateView`
   - UI MUST NOT rerun or reinterpret precheck logic to create a different status

3. Approval eligibility decision
   - Engine computes `DesignerApprovalFlowState.commit_eligible`
   - UI reads approval readiness through `DesignerApprovalStateView.commit_eligible`
   - UI MUST NOT calculate commit eligibility locally

4. Governance policy application
   - Engine applies governance policy and confirmation pressure
   - UI reads the resulting confirmation requirements through preview/precheck/approval state
   - UI MUST NOT reinterpret governance rules to weaken or bypass engine decisions

UI-owned responsibilities are limited to:
- collecting natural-language request input
- displaying engine-generated preview state
- displaying engine-generated precheck/approval state
- collecting approve / reject / request-revision style user actions
- showing governance hints and confirmation requirements without rewriting them

Forbidden UI behaviors:
- generating preview content in the panel layer
- calculating `commit_eligible` from findings in the panel layer
- downgrading `confirmation_required` into a soft warning in the panel layer
- hiding destructive or blocked status because the panel prefers a simpler UX

20. RELATED ENGINE CONTRACTS

The Designer Panel View Model depends on the following engine-side contracts and implementations:
- `docs/specs/designer/designer_governance_contract.md`
- `docs/specs/designer/designer_approval_flow_contract.md`
- `docs/specs/designer/designer_validator_precheck_contract.md`
- `docs/specs/designer/circuit_draft_preview_contract.md`
- `src/designer/preview_builder.py`
- `src/designer/models/designer_approval_flow.py`
- `src/designer/models/validation_precheck.py`
- `src/designer/models/circuit_draft_preview.py`

