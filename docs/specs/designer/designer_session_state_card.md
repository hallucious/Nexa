# Designer Session State Card v0.1

## Recommended save path
`docs/specs/designer/designer_session_state_card.md`

## 1. Purpose

This document defines the canonical input card given to Designer AI
before intent generation.

Its purpose is to ensure that Designer AI operates from:

- current Working Save reality
- explicit modification scope
- available resources
- bounded goals and constraints
- known findings and risks
- proposal-flow state

Designer AI must not infer these implicitly.
They must be provided explicitly.

## 2. Core Decision

Designer AI does not “know Nexa by itself”.

Official rule:

- Designer AI receives a structured session state card.
- The card defines the current design reality and boundaries.
It may also surface persisted approval-ready continuation hints through notes when a commit candidate can be resumed explicitly.
After successful commit, approval-ready continuation must be reduced into a post-commit summary rather than left as a stale resume path.
A new Designer request after commit must start a fresh proposal cycle from the committed baseline instead of inheriting consumed continuation scope, clarification, or revision state.
Repeated fresh cycles must rotate fresh-cycle markers so stale baseline/request markers do not survive into later cycles.
Successful commit must remove stale fresh-cycle markers and reduce them back into compact committed-summary notes.
- Designer AI produces proposals from this card.
- Designer AI must not silently assume hidden structure or hidden authority.

In short:

Designer AI is a bounded proposal producer driven by an explicit session state card.

## 3. Position in the Flow

Canonical flow:

User Request
-> Designer Session State Card
-> Normalized Intent
-> Circuit Patch Plan
-> Validator Precheck
-> Draft Preview
-> Approval
-> Commit

The session state card exists before intent generation.

## 4. Top-Level Shape

DesignerSessionStateCard
- card_version: string
- session_id: string
- storage_role: string
- current_working_save: object
- current_selection: object
- target_scope: object
- available_resources: object
- objective: object
- constraints: object
- current_findings: object
- current_risks: object
- revision_state: object
- approval_state: object
- notes may include post-commit cleanup summary
- notes may include a fresh-cycle-from-committed-baseline marker when a new request is opened after commit
- conversation_context: object
- output_contract: object
- forbidden_authority: object
- notes: optional object

## 5. Required Fields

### 5.1 `card_version`
Version of this card schema.

Example:
- "0.1"

### 5.2 `session_id`
Stable id for the current Designer session.

Purpose:
- track retries
- track revisions
- correlate intent/patch/precheck/preview chain

### 5.3 `storage_role`
Must indicate the current artifact role.

Preferred values:
- "working_save"
- "commit_snapshot"
- "none"

Rules:
- Designer editing sessions should normally operate on `working_save`
- read-only analysis may reference `commit_snapshot`
- Designer must never treat `commit_snapshot` as freely editable draft state

### 5.4 `current_working_save`
The current editable structural reality.

Minimum content:
- savefile_ref
- current_revision
- circuit_summary
- node_list
- edge_list
- output_list
- prompt_refs
- provider_refs
- plugin_refs
- draft_validity_status

Rules:
- incomplete or invalid draft state must still be representable
- this is not optional for create/modify/repair/optimize flows
- if no working save exists, `current_working_save.mode = "empty_draft"` must be explicit

### 5.5 `current_selection`
What the user is currently focused on.

Minimum content:
- selection_mode: none | node | edge | output | subgraph | whole_circuit
- selected_refs: list[string]

Purpose:
- helps bounded modification
- helps patch planning
- prevents wide unintended edits

### 5.6 `target_scope`
The permitted modification boundary.

Minimum content:
- mode: new_circuit | existing_circuit | subgraph_only | node_only | read_only
- touch_budget: minimal | bounded | broad
- allowed_node_refs
- allowed_edge_refs
- allowed_output_refs
- destructive_edit_allowed: bool

Rules:
- read_only means explain/analyze only
- destructive_edit_allowed = false blocks silent delete/replace operations
- missing explicit scope must be treated as ambiguity, not permission

### 5.7 `available_resources`
What resources may be used in the proposal.

Shape:

available_resources
- prompts
- providers
- plugins

Each resource entry should expose:
- id
- availability_status
- version
- tags
- constraints
- notes

Rules:
- unavailable resources must remain visible as unavailable
- Designer must not propose unresolved provider/plugin bindings as if they are ready
- this card is the source of truth for design-time resource availability

### 5.8 `objective`
The design goal.

Minimum content:
- primary_goal
- secondary_goals
- success_criteria
- preferred_behavior

Examples:
- "create a debate-based comparison circuit"
- "repair broken output binding with minimal change"
- "reduce cost without reducing review safety"

### 5.9 `constraints`
The bounded design constraints.

Minimum content:
- cost_limit
- speed_priority
- quality_priority
- determinism_preference
- safety_level
- human_review_required
- provider_preferences
- provider_restrictions
- plugin_preferences
- plugin_restrictions
- output_requirements
- forbidden_patterns

Rules:
- constraints must be treated as hard input, not style hints
- forbidden_patterns must be propagated into intent and patch generation

### 5.10 `current_findings`
Known validation/precheck findings for the current draft.

Minimum content:
- blocking_findings
- warning_findings
- confirmation_findings
- finding_summary

Purpose:
- allows repair-oriented design
- prevents Designer from ignoring current invalid structure
- provides explicit risk context for patch planning

### 5.11 `current_risks`
Known design risks already identified.

Minimum content:
- risk_flags
- severity_summary
- unresolved_high_risks

Examples:
- provider_unavailable
- plugin_missing
- invalid_dependency_shape
- high_cost_design
- destructive_change_risk
- ambiguity_not_resolved

### 5.12 `revision_state`
Tracks the proposal loop status.

Minimum content:
- revision_index
- based_on_intent_id
- based_on_patch_id
- prior_rejection_reasons
- retry_reason
- user_corrections
- last_control_action
- last_terminal_status
- attempt_history

Purpose:
- prevents Designer from forgetting why prior proposals were rejected
- keeps proposal evolution explicit
- preserves bounded retry/fallback history across session rebuilds
- carries clarification and revision context forward when approval decisions request interpretation choice or proposal revision

### 5.13 `approval_state`
Current approval boundary status.

Minimum content:
- approval_required: bool
- approval_status: not_started | pending | approved | rejected
- confirmation_required: bool
- blocking_before_commit: bool

Rules:
- Designer must not act as if approved when approval is pending or rejected
- approval-boundary outcomes that request interpretation or revision must be reflected back into session continuity rather than disappearing after one step

### 5.14 `conversation_context`
A bounded summary of the active design conversation.

Minimum content:
- user_request_text
- clarified_interpretation
- unresolved_questions
- explicit_user_preferences

Rules:
- this is a summary layer, not raw transcript dumping
- unresolved questions must remain visible

### 5.15 `output_contract`
Defines what Designer AI must return.

Minimum content:
- required_primary_output: normalized_intent
- allowed_secondary_outputs:
  - patch_plan
  - explanation
  - ambiguity_report
  - risk_report
- preview_required: bool

Rules:
- Designer must not output raw savefile mutation as primary output
- output must remain proposal-oriented

### 5.16 `forbidden_authority`
Defines what Designer AI is not allowed to do.

Minimum content:
- may_commit_directly: false
- may_redefine_engine_contracts: false
- may_bypass_precheck: false
- may_bypass_preview: false
- may_bypass_approval: false
- may_mutate_committed_truth_directly: false

This section is mandatory.

## 6. Optional Fields

### 6.1 `notes`
Optional auxiliary metadata.

May include:
- UI hints
- designer mode
- preferred explanation style
- business priority notes

Rules:
- optional notes must never override hard constraints

## 7. Minimal Operational Card

The smallest acceptable card for real Designer operation is:

- storage_role
- current_working_save
- target_scope
- available_resources
- objective
- constraints
- current_findings
- revision_state
- output_contract
- forbidden_authority

Anything smaller is too weak for safe design behavior.

## 8. What Must Not Be Injected As Authority

The following must not be injected as Designer authority:

- direct commit permission
- direct runtime contract rewrite permission
- hidden structural mutation permission
- fake approval state
- implicit “full-circuit edit allowed” permission
- implicit resource availability
- implied safety override

If these are needed, they must be made explicit and separately approved.

## 9. Example Shape

Example:

DesignerSessionStateCard
  card_version: "0.1"
  session_id: "designer_session_001"
  storage_role: "working_save"

  current_working_save:
    savefile_ref: "working_save://current"
    current_revision: "rev_12"
    mode: "existing_draft"
    circuit_summary:
      node_count: 6
      edge_count: 7
      output_count: 1
    node_list:
      - "draft_generator"
      - "reviewer"
      - "final_judge"
    edge_list:
      - "draft_generator->reviewer"
      - "reviewer->final_judge"
    output_list:
      - "final_answer"
    prompt_refs:
      - "draft_prompt"
      - "judge_prompt"
    provider_refs:
      - "openai:gpt"
      - "anthropic:claude"
    plugin_refs:
      - "evidence.search"
    draft_validity_status: "warning"

  current_selection:
    selection_mode: "node"
    selected_refs:
      - "reviewer"

  target_scope:
    mode: "node_only"
    touch_budget: "minimal"
    allowed_node_refs:
      - "reviewer"
    allowed_edge_refs: []
    allowed_output_refs: []
    destructive_edit_allowed: false

  available_resources:
    prompts:
      - id: "review_prompt"
        availability_status: "available"
        version: "1.0"
    providers:
      - id: "anthropic:claude"
        availability_status: "available"
        version: "stable"
    plugins:
      - id: "evidence.search"
        availability_status: "available"
        version: "1.2.0"

  objective:
    primary_goal: "improve review quality"
    secondary_goals:
      - "preserve low cost"
    success_criteria:
      - "better critique depth"
      - "no new blocking findings"
    preferred_behavior: "bounded minimal patch"

  constraints:
    cost_limit: "low"
    speed_priority: "medium"
    quality_priority: "high"
    determinism_preference: "medium"
    safety_level: "normal"
    human_review_required: true
    provider_preferences:
      - "anthropic:claude"
    provider_restrictions: []
    plugin_preferences:
      - "evidence.search"
    plugin_restrictions: []
    output_requirements:
      - "normalized_intent"
      - "patch_plan"
    forbidden_patterns:
      - "silent destructive edit"

  current_findings:
    blocking_findings: []
    warning_findings:
      - "review node prompt is too generic"
    confirmation_findings: []
    finding_summary: "warning_only"

  current_risks:
    risk_flags:
      - "quality_drift"
    severity_summary: "low"
    unresolved_high_risks: []

  revision_state:
    revision_index: 2
    based_on_intent_id: "intent_014"
    based_on_patch_id: "patch_014b"
    prior_rejection_reasons:
      - "too broad"
    retry_reason: "narrow patch to selected reviewer node"
    user_corrections:
      - "modify only reviewer node"
    last_control_action: "request_user_revision"
    last_terminal_status: "awaiting_user_input"
    attempt_history:
      - attempt_index: 1
        stage: "precheck"
        outcome: "blocked"
        reason_code: "DESIGNER-PRECHECK-BLOCKED"
        message: "The patch is blocked and must be revised."

  approval_state:
    approval_required: true
    approval_status: "pending"
    confirmation_required: false
    blocking_before_commit: false

  conversation_context:
    user_request_text: "Improve the reviewer node without changing the overall circuit"
    clarified_interpretation: "bounded reviewer-node quality upgrade only"
    unresolved_questions: []
    explicit_user_preferences:
      - "minimal change"

  output_contract:
    required_primary_output: "normalized_intent"
    allowed_secondary_outputs:
      - "patch_plan"
      - "explanation"
      - "risk_report"
    preview_required: true

  forbidden_authority:
    may_commit_directly: false
    may_redefine_engine_contracts: false
    may_bypass_precheck: false
    may_bypass_preview: false
    may_bypass_approval: false
    may_mutate_committed_truth_directly: false

## 10. Decision

Designer AI can operate safely only when its input state is explicit.

The canonical input boundary is the Designer Session State Card.

It must provide:
- current design reality
- bounded scope
- available resources
- goals and constraints
- known findings and risks
- revision and approval state
- forbidden authority

Without this card, Designer AI is under-specified and unsafe.

## 6. Approval-State Continuation Rules

Preferred approval_state status values in session continuity include:
- not_started
- pending
- approved
- rejected
- committed

Post-commit cleanup rules:
- ready-for-commit resume metadata must be removed after successful commit
- approval_state should move to `committed`
- unresolved approval questions should be cleared
- retry_reason should be cleared
- revision history and user corrections may remain for continuity/audit
- committed-summary notes should rotate through a bounded history (current latest + up to 2 older summaries in v0.1)
- stale fresh-cycle / active-baseline notes must not remain inside committed summary state
