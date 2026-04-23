# Preview to Approval Decision Rules v0.1

## Recommended save path
`docs/specs/designer/preview_to_approval_decision_rules.md`

## 1. Purpose

This document defines the canonical rules from:

- `CircuitDraftPreview`
to
- approval decision handling

Its purpose is to ensure that user approval is based on visible proposal state,
not on hidden structural mutation.

## 2. Core Decision

Approval must be driven by visible preview and explicit user action.

Official rule:

- no preview -> no approval
- no explicit approval -> no commit
- blocked preview cannot be treated as approved
- confirmation-required preview must surface the exact decision boundary

## 3. Canonical Approval Outcomes

- `approve`
- `reject`
- `request_revision`
- `narrow_scope`
- `choose_interpretation`
- `defer`

## 4. Approval Rules

### 4.1 Approve
Valid only when:
- preview exists
- status is not blocked
- required confirmation questions are answered

### 4.2 Reject
May happen for any preview status.

### 4.3 Request revision
Use when direction is broadly right but patch/preview needs change.

### 4.4 Narrow scope
Use when proposal is too broad.

### 4.5 Choose interpretation
Use when ambiguity remains between multiple plausible directions.

## 5. Blocked Rule

If preview is blocked:
- approval must not proceed to commit
- only reject or request_revision style outcomes are valid

## 6. Confirmation Rule

If preview is confirmation-required:
- the exact confirmation target must be made explicit
- approval is invalid until that confirmation is answered

## 7. Decision

Approval is an explicit post-preview user decision boundary.
It must never be inferred silently.
