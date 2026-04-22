# Operations Audit and Approval Workflow Specification

## Recommended save path
`docs/specs/ops/ops_audit_and_approval_workflow_spec.md`

## 1. Purpose

This document defines how recommendations, approvals, and executions in the AI-assisted operations layer must be audited and governed.

## 2. Scope

This specification governs:

1. audit event structure,
2. approval levels,
3. recommendation versus execution separation,
4. approval-chain integrity,
5. retention expectations.

## 3. Audit-first rule

Every meaningful AI-assisted operational event must be auditable.

The system must log:

1. what the AI recommended,
2. whether a human approved it,
3. what was actually executed,
4. what the result was.

These must be distinct events or clearly distinguishable event types.

## 4. Minimum audit fields

Each audit event must capture at least:

1. timestamp,
2. actor_type,
3. actor_identity,
4. capability_level,
5. action_category,
6. target_type,
7. target_id,
8. evidence_summary,
9. recommendation_text or execution_text,
10. approval_required flag,
11. approver_identity if applicable,
12. result_status,
13. rollback_reference if applicable.

## 5. Approval levels

Minimum approval levels:

1. `support`
2. `admin`
3. `owner`

The required approval level must be attached to any staged action before execution.

## 6. Approval integrity

No system path may transform an approval-required recommendation into an executed action without recording:

1. who approved it,
2. when they approved it,
3. what evidence they saw,
4. what exact action was approved.

## 7. Recommendation and execution separation

The following must never be collapsed:

1. recommendation,
2. approval,
3. execution,
4. execution result.

A recommendation is not an execution.
An approval is not an execution.
An execution request is not a successful result.

## 8. Retention rule

Audit events must be retained long enough to support:

1. incident reconstruction,
2. operator accountability,
3. support review,
4. policy review,
5. abuse or safety investigation.

Retention policy should be at least as strict as the product's most durable operational audit requirements.

## 9. Tamper-evidence expectation

The audit path should be append-oriented and tamper-evident where practical.

At minimum:
1. audit events should not be silently overwritten,
2. destructive deletion of audit history should be restricted,
3. retroactive edits should be strongly controlled or forbidden.

## 10. Acceptance criteria

A conforming implementation satisfies this specification only if:

1. audit events are structured,
2. approval levels are explicit,
3. recommendation, approval, execution, and result are separable,
4. approval-required actions cannot bypass audit,
5. audit history is retained and reviewable.
