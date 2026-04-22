# AI-Assisted Operations System Specification

## Recommended save path
`docs/specs/ops/ai_assisted_operations_system.md`

## 1. Purpose

This document defines the specification for an AI-assisted operations system for Nexa.

Its purpose is to establish how AI systems may assist human operators in monitoring, interpreting, triaging, and managing Nexa safely during real service operation.

This system is not the user-facing SaaS product itself.
It is an operational assistance layer that sits on top of Nexa's existing product, observability, admin, audit, and recovery surfaces.

The goal is not full autonomy.
The goal is safe, auditable, high-leverage operational assistance.

## 2. Scope

This specification covers:

- operational state reading
- incident summarization
- failure triage
- runbook recommendation
- safe-action recommendation
- approval-gated operational execution
- auditability of AI-assisted operations
- multi-AI role separation when multiple models are used

This specification does not cover:

- end-user product features
- contract review output generation
- customer-facing workflow authoring
- unrestricted autonomous write access
- destructive automation without human approval
- replacement of human operational accountability

## 3. Relationship to Nexa product operation

The AI-assisted operations system must consume operational surfaces that already exist or are defined elsewhere in Nexa.

It must use, not redefine, the following kinds of surfaces:

- run status and execution state
- queue and worker state
- provider health and probe history
- upload quarantine and scan state
- quota and billing state
- admin/support APIs
- action logs and audit logs
- observability summaries
- backup and recovery state
- runbooks and incident procedures

This system is therefore downstream of product operation.
It depends on the SaaS operational base being present.

## 4. Core principles

### 4.1 Human-supervised by default

The default mode is human-supervised assistance.
The system may read and recommend before it may act.

### 4.2 Audit-first

Every AI recommendation, approval, and executed action must be recorded in an auditable form.
Nothing operationally meaningful may happen invisibly.

### 4.3 Least privilege

The system must not receive broad write access by default.
Permissions must be separated by capability level.

### 4.4 Recommendation before execution

The system should prefer:
- summarizing
- classifying
- ranking
- recommending
- linking runbooks

before it is allowed to trigger even low-risk actions.

### 4.5 Safe operational usefulness over maximal autonomy

The system should optimize for reducing operator burden and improving response quality, not for pretending to be a fully autonomous operator.

## 5. Capability levels

The system must separate operational capability into explicit levels.

### 5.1 Read-only

Permitted examples:

- summarize failed runs
- summarize queue backlog
- summarize provider outages
- summarize quota breaches
- summarize backup verification results
- summarize recent incidents
- summarize webhook failures

Read-only capability must never mutate production state.

### 5.2 Recommend-only

Permitted examples:

- recommend retry candidates
- recommend quarantine review priorities
- recommend quota resets for support review
- recommend webhook replay candidates
- recommend provider failover candidates
- recommend runbook selection
- recommend incident severity

Recommend-only capability must not directly execute the recommendation.

### 5.3 Safe-execute

This level is allowed only for explicitly whitelisted, low-risk, reversible or non-destructive actions.

Permitted examples may include:

- trigger health probe
- refresh derived cache
- generate diagnostic report bundle
- launch non-destructive cleanup job
- re-run safe observability aggregation

Safe-execute must remain narrow and enumerated.

### 5.4 Approval-required execute

These actions may be prepared by AI but require explicit human approval before execution.

Examples:

- retry failed job
- force-reset stuck job
- replay billing webhook
- apply temporary quota override
- re-open or requeue orphaned work item
- restore upload from quarantine override
- trigger provider routing change

### 5.5 Forbidden autonomous actions

The following must remain forbidden for autonomous execution:

- user deletion
- billing state mutation without approval
- provider secret rotation
- auth configuration change
- global quota policy change
- production database restore
- production data purge outside approved retention workflows
- disabling safety, monitoring, or audit systems

## 6. Required data sources

A conforming implementation must read from clearly defined operational sources.

Minimum required source categories:

- run records
- queue job state
- worker lease and orphan state
- provider health state
- provider probe history
- upload safety state
- upload rejection history
- quota usage state
- subscription and billing state
- recent activity summaries
- run action logs
- admin action audit logs
- error tracking summaries
- metrics and traces summaries
- backup verification status
- scheduled cleanup job outcomes
- runbook metadata

The system should prefer structured and summarized sources over raw payloads whenever possible.

## 7. Privacy, redaction, and data handling rules

The AI-assisted operations system must inherit or exceed the existing observability and privacy redaction rules.

It must not consume or emit any of the following unless separately and explicitly approved under a stricter policy:

- raw document text
- prompt-rendered user content
- provider raw outputs containing customer content
- credentials or tokens
- JWTs
- presigned URLs
- raw API keys
- unrestricted PII

If diagnostic context is needed, the operational system must consume one of the following instead:

- redacted summaries
- hashed identifiers
- opaque internal references
- policy-approved diagnostic extracts

The system must never use confidential user content as a convenience shortcut for operational reasoning.

## 8. Operational reasoning outputs

The system should emit structured operational outputs rather than unstructured prose only.

Recommended output fields:

- issue_type
- confidence
- severity
- affected_scope
- probable_root_cause
- recommended_next_action
- required_approval_level
- linked_runbook
- evidence_bundle_ref
- urgency_rank
- actor_permission_required

These outputs must be machine-sortable, human-readable, and auditable.

## 9. Runbook integration

The AI-assisted operations system must map incident classes to explicit runbooks.

Minimum runbook classes should include:

- database restore
- Redis loss or queue corruption
- object storage incident
- stuck worker or queue backlog
- provider outage
- billing reconciliation
- upload quarantine incident
- quota incident
- webhook delivery incident

The system should first recommend the correct runbook, then recommend the next action inside that runbook.

## 10. Audit requirements

Every AI-assisted operational event must be captured in audit history.

Minimum audit fields:

- timestamp
- actor_type (`human`, `ai_assistant`, `automation`)
- actor_identity
- capability_level used
- action_category
- target_type
- target_id
- evidence_summary
- recommendation_text
- required_approval_level
- approver_identity if approved
- executed_action
- result_status
- rollback_reference if applicable

Recommendations and executed actions must be distinguishable.
A recommendation must not be logged as if it were an executed action.

## 11. Human approval model

The system must support approval separation.

Minimum approval levels:

- support-level approval
- admin-level approval
- owner-level approval

The approval model must reflect action risk.
Low-risk support actions may be support-approvable.
Billing, data, authentication, and recovery actions require stronger approval.

The system must not assume all operators are equal.

## 12. Operational UX goals

The system should help human operators:

- understand what failed
- understand who is affected
- understand what is safe to do next
- find the correct runbook quickly
- avoid manual SQL or dashboard hopping where possible
- reduce duplicated investigation work
- preserve a clean audit trail
- respond faster without weakening control boundaries

The objective is not operator replacement.
The objective is better operator leverage.

## 13. Automation boundaries

The specification must distinguish:

- what may be fully automated
- what may be semi-automated
- what must remain manual

### 13.1 Good candidates for full automation

Examples:

- scheduled health probes
- stale cache refresh
- low-risk cleanup jobs
- periodic incident summaries
- backup verification summaries
- routine report generation

### 13.2 Good candidates for semi-automation

Examples:

- retry candidate generation
- quarantine review prioritization
- webhook replay recommendation
- cost spike anomaly detection with human review
- provider failover suggestion

### 13.3 Manual-only candidates

Examples:

- production restore
- user deletion
- billing correction
- global quota changes
- auth mode changes
- secret rotation
- legal or compliance-affecting overrides

## 14. Multi-AI collaboration model

If multiple AI systems are used, their roles must be separated explicitly.

Possible role split:

- summarizer model
- policy classification model
- remediation recommendation model
- human-facing explanation model

The system must not assume that every model has the same trust level, permission level, or data access level.

Multi-AI collaboration should reduce ambiguity, not multiply risk.

## 15. Failure modes of the operations AI system

The specification must explicitly account for failure modes in the ops AI layer itself.

Minimum failure modes:

- hallucinated diagnosis
- unsafe recommendation
- stale-state interpretation
- duplicated action recommendation
- overconfident recommendation despite missing evidence
- recommendation based on redacted-away critical context
- sensitive data leakage in summaries
- excessive alert amplification
- operator over-trust in AI output
- model outage during incident response

Each failure mode must have mitigation rules.

Examples of mitigations:

- confidence labeling
- evidence linking
- approval gating
- recommendation deduplication
- redaction enforcement
- model fallback or degraded mode
- mandatory human confirmation for risky actions

## 16. Rollout path

The rollout path must be staged.

### Stage 1 — Read-only incident summarizer

Capabilities:

- summarize failures
- summarize queue state
- summarize provider health
- summarize quota and billing anomalies
- link runbooks

### Stage 2 — Recommendation engine

Capabilities:

- recommend retry/requeue candidates
- recommend support actions
- recommend runbooks and priority ordering
- generate evidence bundles

### Stage 3 — Approval-gated operational actions

Capabilities:

- trigger approved low-risk actions after operator approval
- log approval and execution chain
- perform narrow support workflows safely

### Stage 4 — Narrow autonomous housekeeping

Capabilities:

- low-risk cleanup
- safe health probes
- routine summarization
- non-destructive maintenance only

Broad autonomous operational control is out of scope.

## 17. Acceptance criteria

A conforming first version should be accepted only if all of the following are true:

1. it can summarize real operational state from live operational sources,
2. it does not require raw confidential user content,
3. it clearly separates read, recommend, and act permissions,
4. it preserves explicit approval boundaries,
5. it records AI recommendations and human-approved actions distinctly,
6. it links recommendations to explicit runbooks,
7. it does not autonomously perform destructive actions,
8. it measurably reduces operator investigation burden,
9. it preserves auditability under normal and incident conditions.

## 18. Relationship to future implementation

This document defines the behavior and governance of the AI-assisted operations feature area.

Concrete implementation planning should be defined in a separate implementation plan after the SaaS operational base is sufficiently present.

That implementation plan may define:

- file changes
- rollout sequence
- model choices
- permission boundaries in code
- operational UIs or APIs
- staged release criteria

If an implementation plan conflicts with this specification on behavior, approval boundaries, or audit requirements, this specification governs.
