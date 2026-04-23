# Designer Approval Flow Contract v0.1

## 1. Purpose

This contract defines the canonical approval boundary for Designer AI proposals.

It ensures no proposal silently becomes committed structure when explicit approval is required.

## 2. Core Principles

1. Approval is a first-class system step.
2. Proposals may be previewed automatically, but commit must respect approval policy.
3. Blocking findings always override approval.
4. Confirmation-required proposals must not auto-commit.
5. User decisions must be explicit and traceable.
6. Reject / revise / narrow-scope paths must be supported.

## 3. ApprovalFlowState Schema

```text
ApprovalFlowState
- approval_id
- intent_ref
- patch_ref
- precheck_ref
- preview_ref
- current_stage
- approval_policy
- required_decision_points
- current_decision_point_id
- user_decisions
- final_outcome
- explanation
```

## 4. Decision Points

Examples:
- full proposal approval
- destructive change confirmation
- provider replacement confirmation
- output semantics change confirmation
- broad-scope change confirmation
- ambiguity resolution
- safety acknowledgment

## 5. User Decision Options

Supported outcomes:
- approve
- reject
- request_revision
- narrow_scope
- choose_interpretation
- abort

## 6. Auto-Commit Rule

Auto-commit is allowed only if:
- no blocking findings
- no required unanswered decision points
- no destructive edit
- no major output semantic change
- no critical provider replacement
- policy explicitly allows it

## 7. Commit Eligibility Rule

Commit is allowed only if:
- no unresolved blocking findings
- all required decision points are answered
- approval outcome is approved_for_commit
- approved scope matches validated preview scope
  or narrowed scope has been revalidated

## 8. Decision

Designer AI may propose.
Validator may assess.
Preview may explain.
Approval flow decides whether a proposal may cross the commit boundary.
