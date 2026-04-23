# AI-Assisted Operations Implementation Plan

## Recommended save path
`docs/implementation/ops/ai_assisted_operations_implementation_plan.md`

## 1. Purpose

This document defines the implementation plan for the Nexa AI-assisted operations system.

Its purpose is to translate the approved operations specification family into a build sequence that can be executed safely and incrementally.

This document is an implementation plan.
It does not replace the operations specifications.
If implementation detail conflicts with behavior or safety rules defined in the operations specifications, the specifications govern.

## 2. Governing references

This implementation plan is downstream of the following documents:

- `docs/specs/ops/ai_assisted_operations_system_index.md`
- `docs/specs/ops/ops_capability_levels_and_permission_spec.md`
- `docs/specs/ops/ops_data_source_and_access_control_spec.md`
- `docs/specs/ops/ops_redaction_and_sensitive_data_handling_spec.md`
- `docs/specs/ops/ops_decision_output_and_runbook_integration_spec.md`
- `docs/specs/ops/ops_audit_and_approval_workflow_spec.md`
- `docs/specs/ops/ops_automation_boundary_and_action_execution_spec.md`
- `docs/specs/ops/ops_multi_agent_coordination_spec.md`
- `docs/specs/ops/ops_failure_mode_and_safety_control_spec.md`
- `docs/specs/ops/ops_rollout_and_acceptance_spec.md`

This plan also depends on the SaaS operational base being sufficiently present, including:

- observability surfaces
- admin/support APIs
- action audit surfaces
- queue and worker state
- provider health state
- backup and recovery state
- quota and billing state

## 3. Non-goals

This plan does not implement:

- end-user product features
- contract review logic
- frontend product UX unrelated to operations
- unrestricted autonomous write access
- destructive autonomous actions
- replacement of human operational accountability

## 4. Implementation philosophy

The implementation must follow these rules:

1. Build read capability before recommendation capability.
2. Build recommendation capability before execution capability.
3. Keep action execution narrow, explicit, and approval-gated.
4. Prefer existing operational surfaces over new deep integrations.
5. Preserve redaction and least-privilege boundaries at every stage.
6. Treat auditability as a first-class requirement, not a final polish step.

## 5. Preconditions

The following must be true before implementation begins:

1. The approved operations spec family is treated as authoritative.
2. The SaaS operational base exposes enough structured state to support read-only operational reasoning.
3. Admin identity and role boundaries already exist or are defined clearly enough to gate operator actions.
4. Runbooks exist or are stubbed for the major incident classes.
5. Audit storage exists or can be extended without violating existing append-only and governance rules.

If any of these are false, implementation must stop and the missing precondition must be closed first.

## 6. Required source surfaces

The implementation must consume structured operational sources before introducing new derived layers.

Minimum source categories:

- run status and run lifecycle events
- queue job state and worker state
- provider health and probe history
- upload quarantine and scan state
- quota and billing state
- backup verification state
- cleanup job state
- audit logs
- admin action logs
- observability summaries
- runbook metadata

Where both raw and summarized forms exist, summarized forms must be preferred.

## 7. Delivery model

The implementation proceeds through four stages:

- Stage A: Read-only operational insight
- Stage B: Recommendation and decision structuring
- Stage C: Approval-gated safe action execution
- Stage D: Narrow autonomous housekeeping

A stage must not start until the previous stage's acceptance criteria are met.

## 8. Stage A — Read-only operational insight

### 8.1 Goal

Provide operators with AI-generated summaries of operational state without granting write or execution capability.

### 8.2 Capabilities delivered

- failed-run summarization
- queue backlog summarization
- stuck-job summarization
- provider-outage summarization
- quota/billing anomaly summarization
- backup/restore state summarization
- recent incident summary generation
- runbook suggestion based on issue class

### 8.3 New implementation surfaces

Recommended files:

- `src/ops_ai/__init__.py`
- `src/ops_ai/models.py`
- `src/ops_ai/read_models.py`
- `src/ops_ai/source_registry.py`
- `src/ops_ai/summarizers.py`
- `src/ops_ai/runbook_router.py`
- `src/ops_ai/redaction_gate.py`
- `src/ops_ai/api.py`

### 8.4 Data contracts

The read layer must define explicit typed models for:

- operational issue summary
- affected scope summary
- evidence bundle reference
- runbook recommendation
- confidence and severity labeling

The read layer must not pass raw confidential payloads to models.

### 8.5 API surface

Recommended internal routes:

- `GET /api/admin/ops/summary`
- `GET /api/admin/ops/issues`
- `GET /api/admin/ops/issues/{issue_id}`
- `GET /api/admin/ops/runbooks/recommendations`

These routes are internal/admin-only.

### 8.6 Safety requirements

- no write capability
- no admin mutation calls
- no direct access to raw user document content
- all model inputs pass through redaction gate
- all outputs logged as AI-read summaries only

### 8.7 Exit criteria

Stage A is complete only if:

1. operators can retrieve AI summaries for real operational state,
2. summaries link to evidence bundles,
3. summaries link to candidate runbooks,
4. no write action is possible from the Stage A surface,
5. audit records distinguish AI summary generation from human action.

## 9. Stage B — Recommendation and decision structuring

### 9.1 Goal

Add recommendation capability without allowing direct execution.

### 9.2 Capabilities delivered

- recommended retry candidates
- recommended stuck-job handling candidates
- recommended quarantine review ordering
- recommended webhook replay targets
- recommended quota override candidates
- recommended incident severity and urgency ranking
- recommended next action with required approval level

### 9.3 New implementation surfaces

Recommended files:

- `src/ops_ai/recommendation_models.py`
- `src/ops_ai/recommendation_engine.py`
- `src/ops_ai/priority_ranker.py`
- `src/ops_ai/evidence_builder.py`
- `src/ops_ai/approval_classifier.py`

### 9.4 Output requirements

Every recommendation must include:

- recommendation id
- issue type
- confidence
- severity
- affected scope
- recommended next action
- required approval level
- evidence references
- linked runbook
- expiration or staleness marker

### 9.5 Safety requirements

- recommendations must not trigger side effects
- duplicate recommendations must be deduplicated
- stale recommendations must be marked stale
- low-confidence recommendations must be labeled explicitly
- recommendations must remain separate from executed actions in audit logs

### 9.6 Exit criteria

Stage B is complete only if:

1. recommendation outputs are structured and queryable,
2. operators can see why a recommendation was made,
3. each recommendation maps to approval level and runbook,
4. no recommendation can be auto-executed from the recommendation layer,
5. recommendation history is auditable.

## 10. Stage C — Approval-gated safe action execution

### 10.1 Goal

Enable narrow operational actions through explicit approval workflow.

### 10.2 Capabilities delivered

Examples of allowed initial actions:

- trigger provider probe
- trigger safe diagnostic bundle generation
- retry failed job after approval
- force-reset stuck job after approval
- replay webhook after approval
- apply temporary quota reset after approval

### 10.3 Forbidden actions at this stage

- user deletion
- subscription mutation without explicit owner/admin workflow
- secret rotation
- auth configuration changes
- production restore
- global quota policy changes

### 10.4 New implementation surfaces

Recommended files:

- `src/ops_ai/action_models.py`
- `src/ops_ai/action_registry.py`
- `src/ops_ai/action_executor.py`
- `src/ops_ai/approval_workflow.py`
- `src/ops_ai/audit_writer.py`
- `src/ops_ai/api_actions.py`

### 10.5 Execution contract

Every action request must include:

- action id
- action type
- target type
- target id
- proposed by
- approval level required
- approval state
- execution state
- rollback possibility
- result summary

### 10.6 Approval requirements

Actions must remain blocked until:

- approver identity is verified
- approver role satisfies required approval level
- evidence bundle is attached
- recommendation is not stale
- target still exists and is still eligible

### 10.7 Exit criteria

Stage C is complete only if:

1. at least one safe action path works end-to-end,
2. approval and execution are logged separately,
3. rejected approvals are logged,
4. executed actions remain narrow and reversible where possible,
5. forbidden actions cannot be routed through the same execution path.

## 11. Stage D — Narrow autonomous housekeeping

### 11.1 Goal

Allow low-risk autonomous operations only after earlier stages are stable.

### 11.2 Allowed automation category

Examples:

- periodic operational summaries
- routine health probe scheduling
- stale cache refresh
- cleanup candidate generation
- non-destructive maintenance actions already allowed in policy

### 11.3 Safety rules

Autonomous housekeeping must:

- operate only on whitelisted action types
- remain bounded by schedule and rate limits
- log every execution as automation
- stop automatically on repeated failure
- never escalate into destructive or policy-sensitive actions

### 11.4 New implementation surfaces

Recommended files:

- `src/ops_ai/automation_scheduler.py`
- `src/ops_ai/automation_policy.py`
- `src/ops_ai/automation_guard.py`

### 11.5 Exit criteria

Stage D is complete only if:

1. automation scope is explicitly enumerated,
2. automated actions are low-risk and non-destructive,
3. automation can be disabled centrally,
4. repeated failures cause automatic suspension,
5. all executions remain auditable.

## 12. Suggested repository layout

Recommended save paths:

- `docs/specs/ops/ai_assisted_operations_system_index.md`
- `docs/implementation/ops/ai_assisted_operations_implementation_plan.md`

Recommended code layout:

- `src/ops_ai/`
- `tests/ops_ai/`

Suggested test families:

- `tests/ops_ai/test_redaction_gate.py`
- `tests/ops_ai/test_source_registry.py`
- `tests/ops_ai/test_summary_generation.py`
- `tests/ops_ai/test_recommendation_structuring.py`
- `tests/ops_ai/test_approval_workflow.py`
- `tests/ops_ai/test_action_execution_boundaries.py`
- `tests/ops_ai/test_automation_guard.py`
- `tests/ops_ai/test_audit_integrity.py`

## 13. Permission model

The implementation must encode capability levels directly in policy, not only in UI.

Minimum policy levels:

- read_only
- recommend_only
- safe_execute
- approval_required_execute
- forbidden

Each AI-facing tool or operation must map to one of these levels.

The system must never infer permission from prompt text alone.

## 14. Redaction architecture

The implementation must place redaction before AI model invocation.

Recommended order:

1. fetch structured operational source
2. project source into safe diagnostic view
3. redact sensitive fields
4. attach opaque identifiers where needed
5. invoke model
6. validate output structure
7. write audit summary

The model must not see raw confidential fields and then rely on output filtering afterward.

## 15. Runbook architecture

The implementation must treat runbooks as structured operational objects.

Minimum runbook fields:

- runbook_id
- title
- incident_class
- severity_band
- preconditions
- step list
- escalation rule
- rollback notes
- linked admin actions
- approval level required

Recommendations should point to runbook ids, not only prose titles.

## 16. Audit model

The implementation must preserve these audit distinctions:

- AI summary generated
- AI recommendation generated
- approval requested
- approval granted or denied
- action executed
- action failed
- rollback executed
- automation executed
- automation suspended

These are separate events and must be stored separately or as separately typed audit rows.

## 17. Failure handling in the ops AI layer

The implementation must explicitly handle:

- model failure
- malformed model output
- stale input state
- missing evidence
- redaction over-strip causing weak diagnosis
- duplicate recommendation generation
- action execution refusal
- approval race conditions

Each class must produce deterministic operator-facing fallback behavior.

Examples:

- malformed model output → fall back to templated summary
- missing evidence → emit low-confidence recommendation with explicit warning
- stale state → require refresh before approval
- approval race → reject duplicate execution

## 18. Rollout gate table

### Gate 1 — Read-only ready
Requirements:
- Stage A complete
- redaction gate tested
- audit summary logging works

### Gate 2 — Recommendation ready
Requirements:
- Stage B complete
- structured recommendation objects stable
- operator feedback loop available

### Gate 3 — Approval-execution ready
Requirements:
- Stage C complete
- approval workflow tested
- action registry whitelisted
- forbidden actions blocked

### Gate 4 — Narrow autonomy ready
Requirements:
- Stage D complete
- automation guard tested
- kill switch available
- repeated-failure suspension tested

## 19. Acceptance criteria

The full implementation plan is satisfied only if:

1. implementation follows the staged model,
2. redaction happens before model invocation,
3. the system is useful in read-only mode before any action mode is enabled,
4. recommendation outputs are structured and auditable,
5. action execution remains approval-gated except for explicitly whitelisted housekeeping,
6. forbidden destructive actions remain inaccessible,
7. audit logs distinguish recommendation, approval, execution, and automation,
8. the system improves operator efficiency without weakening control boundaries.

## 20. Final implementation rule

If there is ambiguity during implementation, choose the option that:

1. preserves the governing ops specifications,
2. reduces privilege,
3. preserves auditability,
4. delays risky automation rather than accelerating it,
5. keeps destructive authority under explicit human control.
