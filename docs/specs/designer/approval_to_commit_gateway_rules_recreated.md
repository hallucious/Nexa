# Approval to Commit Gateway Rules v0.1

## Recommended save path
`docs/specs/designer/approval_to_commit_gateway_rules.md`

## 1. Purpose

This document defines the canonical rules from:

- approval outcome
to
- commit gateway behavior

Its purpose is to ensure that only approved, non-blocked, boundary-compliant proposals
cross into committed structural truth.

## 2. Core Decision

Commit is a hard truth boundary.

Official rule:

- only explicitly approved proposals may enter commit gateway
- blocked proposals must never commit
- rejected proposals must never commit
- revision-requested proposals must return to proposal flow, not commit
- commit must preserve approval truth and storage-role truth

## 3. Commit Eligibility Rules

A proposal is commit-eligible only when all are true:

1. preview exists
2. approval outcome is `approve`
3. no blocking findings remain
4. confirmation-required items are resolved
5. forbidden authority boundaries were not violated
6. target artifact is still consistent with the approved base revision

## 4. Commit Rejection Rules

Commit must be rejected when:
- approval is missing
- approval is rejected
- preview is blocked
- base revision drift invalidates approval
- unresolved required confirmation remains
- proposal exceeded its authority boundary

## 5. Commit Gateway Duties

The gateway must:
- verify approval truth
- verify current base revision
- verify no blocked findings remain
- verify storage-role correctness
- create approved structural state only after successful checks

## 6. Working Save vs Commit Snapshot Rule

Commit gateway must convert approved proposal into committed structural truth,
not carry forward draft-only convenience state as if it were approved truth.

## 7. Decision

Commit is not a continuation of proposal generation.
It is a separate guarded truth boundary that requires explicit approval and clean eligibility.
