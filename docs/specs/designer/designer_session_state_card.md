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
Committed-summary exposure must remain priority-aware: the latest committed summary is primary, while older retained summaries are exposed only as low-priority history/reference context.
Referential requests such as "previous change" or "last commit" must bias interpretation toward the latest committed summary first unless the user clarifies otherwise.
Repeated referential confirmation loops may raise a control-governance tier that requires a stronger anchor before auto-resolution resumes.
If a later referential retry already provides the stronger anchor, stale pending-anchor carryover should be cleared and reduced into a low-priority resolution summary rather than staying active.
If the user explicitly redirects scope away from the latest clarified revision thread, that older approval/revision continuity must be archived out of active continuity and retained only as low-priority background context.
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
- notes may include control-governance policy tier, repeat-loop summaries, and referential-anchor requirements when repeated confirmation cycles tighten interpretation safety
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
- session-card notes may expose committed-summary priority metadata, including latest-summary-primary and history-reference-only semantics
- referential request normalization must treat the latest committed summary as the primary baseline and older retained summaries as ambiguity context rather than equal-priority truth
- stale fresh-cycle / active-baseline notes must not remain inside committed summary state


- reference_resolution_policy: latest committed summary may auto-resolve generic last/previous references; second-latest and exact commit-id references are allowed when explicit; non-latest older references without a precise anchor must remain explicit ambiguities.


- `committed_summary_target_resolution_policy`: target-resolution policy string
- `committed_summary_target_auto_resolution_modes`: list of safe auto-target modes
- `committed_summary_target_clarification_required_modes`: list of target modes that must remain explicit
- `committed_summary_action_resolution_policy`: action-resolution policy string
- `committed_summary_action_auto_resolution_modes`: list of safe auto-action modes
- `committed_summary_action_clarification_required_modes`: list of mixed or unsafe action modes that must remain explicit

Target-resolution rule:
- a referenced committed summary may auto-select a patch target only when it exposes exactly one touched node and the request does not specify a conflicting explicit node target
- if the referenced summary touched multiple nodes, or the explicit request target conflicts with the referenced summary target set, Designer must keep the request confirmation-bounded

Action-resolution rule:
- safe auto-action resolution is intentionally narrow in Phase 2
- only revert / undo / rollback language may auto-resolve into a bounded `revert_committed_change` action
- this auto-resolution is allowed only when the committed summary reference is safely resolved and the request does not mix revert language with a second structural-edit intent such as provider replacement, plugin attachment, rename, insert, optimize, or repair
- mixed-action requests must remain explicit confirmation-bounded requests rather than being auto-expanded into multi-step action plans
- when mixed referential action language is detected, Designer should emit a generic clarification flag plus a reason-like mixed-action code (for example provider-change or plugin-attach), should avoid auto-emitting partial structural actions, and should surface that reason into precheck/preview confirmation messaging


## 12. Designer-bounded mixed referential reason codes

- mixed referential confirmation reasons remain Designer-bounded for now and are not promoted into the shared platform-wide reason-code catalog
- the canonical bounded catalog lives in `src/designer/reason_codes.py`
- normalizer / patch / precheck / preview must reuse that bounded catalog instead of duplicating string literals
- promotion into a broader shared reason-code system is deferred until UI and real usage testing justify it


- Proposal-control/session-state integration now preserves Designer-bounded mixed referential reason codes in attempt history and session notes (`last_attempt_reason_code`, `last_attempt_stage`, `last_attempt_outcome`).
- Approval-resolution revision flow now reuses the same Designer-bounded mixed referential reason code when a revision is requested after confirmation, and persists it into `revision_state.retry_reason` plus `notes.last_revision_reason_code`.
- Mixed referential reason retention now has an explicit lifecycle boundary: active session-note markers are used only during the live revision cycle; post-commit cleanup archives the latest mixed reason into compact history-only notes; fresh unrelated cycles clear transient mixed-reason markers before new request interpretation begins.
- Repeated confirmation cycles now produce control-governance notes derived from recent attempt history. These notes summarize recent attempts, repeat counts, and whether stricter referential interpretation safety should be applied in the next cycle.
- When repeated confirmation cycles remain unresolved, referential auto-resolution must temporarily tighten: rollback/undo language should require an explicit commit anchor, explicit node target, or explicit non-latest selector before safe automatic resolution resumes.
- Governance tier handling is now request-applicability-aware. Elevated/strict referential governance should only surface when the current request is actually in the risky referential category; already-anchored requests may downgrade to warning-style surfacing while the elevated tier remains active.
- Governance policy is now reused across approval/revision safety. Governance-derived approval decisions may carry explicit next-step anchor guidance, and governance-triggered revision requests may persist anchor guidance into session notes/unresolved questions for the next attempt.


- safe non-referential cycles now contribute explicit decay progress; after enough consecutive safe cycles, elevated/strict governance can deescalate one tier even without a new referential anchor event
- Governance notes now also carry an explicit ambiguity-pressure score/band so long-horizon escalation, anchored relief, and safe-cycle decay can be inspected numerically instead of only via tier labels.
- Governance pressure is no longer notes-only. When applicable, preview/precheck/approval guidance may reuse pressure summaries so the current request can see whether ambiguity pressure is still building, held, or already easing inside the active tier.

* revision-request continuity now persists structured governance guidance, including anchor requirement mode, pressure summary/score/band, and next-safe-action hints so the next cycle inherits pressure-aware anchor guidance instead of only a generic note
* cleared governance carryover may survive for one nearby follow-up cycle as low-priority recent-resolution context, but it should expire after that short window rather than lingering indefinitely in session continuity

* approval-boundary continuation now keeps a compact recent revision history (bounded) so rebuilt session cards and the normalizer can recognize longer multi-step revision threads and preserve the latest clarified direction unless the user explicitly redirects scope

* compact recent approval/revision continuity is now redirect-aware: if a new mutation request explicitly redirects scope away from the latest clarified interpretation, rebuilt session cards and normalization retain the old thread only as background history instead of surfacing it as active continuity pressure; if the user later explicitly returns to that older scope, the archived thread is restored as active continuity again
* active compact approval/revision continuity history now has a short-lived retention window and expires after a nearby follow-up cycle unless a newer revision thread refreshes it


- Redirected recent revision threads are archived out of active continuity using `approval_revision_redirect_archived_*` notes and are cleared when a new active revision thread forms.
- When the user explicitly reopens that older scope, rebuilt session cards may persist `approval_revision_recent_history_reopened_*` notes so the restored thread is treated as reopened continuity rather than ordinary recent-history reuse.
