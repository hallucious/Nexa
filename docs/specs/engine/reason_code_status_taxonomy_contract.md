# Reason Code and Status Taxonomy Contract

## Recommended save path
`docs/specs/engine/reason_code_status_taxonomy_contract.md`

## 1. Purpose

This document defines the canonical status-family and reason-code taxonomy used across Stage 1 engine contracts in Nexa.

Its purpose is to prevent subsystem drift where automation, safety, quota, execution, streaming, and delivery all invent incompatible status names and opaque failure labels.

This contract exists because stable product behavior requires stable machine-readable semantics.

## 2. Core Decision

Every Stage 1 subsystem may have its own local statuses,
but all externally visible engine truth must map to a canonical taxonomy.

Official rule:

- statuses must belong to explicit status families
- reason codes must be machine-usable and subsystem-stable
- human summaries may vary by UI mode, but underlying codes must remain stable
- a reason code must never silently change category meaning over time

In short:

Nexa must speak one internal status language even when many subsystems participate.

## 3. Canonical Status Families

The minimum canonical families are:

1. launch_status
2. safety_status
3. quota_status
4. execution_status
5. streaming_status
6. delivery_status

## 4. Status Family Definitions

### 4.1 launch_status
- requested
- allowed
- blocked
- cancelled
- confirmation_required

### 4.2 safety_status
- safe
- warning
- blocked
- confirmation_required
- unknown

### 4.3 quota_status
- within_limit
- near_limit
- blocked
- unknown

### 4.4 execution_status
- queued
- running
- completed
- failed
- cancelled
- partial
- unknown

### 4.5 streaming_status
- unavailable
- available
- active
- paused
- completed
- terminated
- unknown

### 4.6 delivery_status
- not_attempted
- pending
- sending
- succeeded
- failed
- blocked
- cancelled
- unknown

## 5. Reason Code Structure

Canonical format:

`<subsystem>.<category>.<specific_reason>`

Examples:
- `safety.credential.exposed_secret_pattern`
- `safety.policy.blocked_content`
- `quota.user.monthly_cost_limit_exceeded`
- `quota.workspace.daily_run_limit_near_threshold`
- `launch.confirmation.user_ack_required`
- `execution.provider.timeout`
- `execution.runtime.unhandled_exception`
- `delivery.destination.auth_failed`
- `delivery.payload.unsupported_shape`

## 6. Minimum Required Reason Code Fields

ReasonCodeRecord
- code: string
- subsystem: enum("launch", "safety", "quota", "execution", "streaming", "delivery")
- severity: enum("info", "warning", "blocking", "failure")
- family: string
- human_summary: string
- recommended_next_action: optional string

## 7. Mapping Rules

### 7.1 One event may carry multiple reason codes
Example:
- execution completed
- delivery blocked due to outbound policy

### 7.2 One reason code must map to one primary subsystem
Avoid ambiguous codes like:
- `general.failed`
- `runtime.problem`
- `error.unknown` as default catch-alls

### 7.3 Human wording may vary, code may not
Beginner UI may say:
- “This run was blocked because your input may contain a secret.”

Advanced UI may say:
- `safety.credential.exposed_secret_pattern`

Both must map to the same underlying code.

## 8. Anti-Ambiguity Rules

The following are forbidden as canonical outward-facing codes:
- `unknown_error` as the default first label
- `failed` with no subsystem family
- `blocked` with no family or basis
- delivery failure codes reused for execution failure
- safety block codes reused for quota block

Unknown states may exist internally,
but canonical outward truth must be narrowed before presentation whenever possible.

## 9. Relationship to UI

UI may:
- translate
- compress
- group
- simplify
- localize

UI may not:
- invent new engine truth categories
- merge distinct canonical families into one engine state
- drop subsystem identity from audit/export surfaces

## 10. Relationship to Logs, Trace, and Audit

Reason codes must be usable in:
- trace timelines
- run history
- delivery history
- quota reports
- safety audits
- future analytics/reporting

Therefore:
- codes should remain stable across versions where possible
- deprecated codes should map forward explicitly
- code churn should be minimized

## 11. Initial Canonical Examples

### Safety
- `safety.credential.exposed_secret_pattern`
- `safety.personal.detected_personal_data_warning`
- `safety.policy.confirmation_required_sensitive_input`
- `safety.policy.blocked_content`

### Quota
- `quota.user.daily_run_limit_exceeded`
- `quota.user.monthly_cost_limit_exceeded`
- `quota.workspace.delivery_action_limit_exceeded`
- `quota.workspace.near_threshold_warning`

### Execution
- `execution.provider.timeout`
- `execution.provider.rate_limited`
- `execution.runtime.unhandled_exception`
- `execution.runtime.cancelled_by_user`

### Delivery
- `delivery.destination.auth_failed`
- `delivery.destination.unreachable`
- `delivery.payload.unsupported_shape`
- `delivery.policy.outbound_blocked`

## 12. Explicit Non-Goals

This v1 contract does not define:
- full analytics schema
- legal/compliance retention categories
- pricing/billing terminology
- end-user UI copy in all languages

## 13. Final Statement

Nexa must maintain a stable, subsystem-aware status and reason-code taxonomy.

Without a shared status language,
Stage 1 contracts will appear integrated on paper but remain ambiguous in practice.