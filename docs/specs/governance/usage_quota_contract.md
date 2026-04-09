# Usage Quota Contract

## Recommended save path
`docs/specs/governance/usage_quota_contract.md`

## 1. Purpose

This document defines the canonical usage-quota contract for Nexa when engine-level contract changes are allowed.

Its purpose is to prevent runaway cost, overuse, and uncontrolled automation at user, workspace, and system levels.

This contract exists because budgeting inside a single run is not enough.
General-user product reality also requires limits such as:
- daily run count
- monthly cost ceiling
- automation volume cap
- destination delivery cap
- streaming/runtime usage ceiling

Usage quota must therefore become an explicit governance contract,
not a hidden billing afterthought.

## 2. Core Decision

Quota must be enforced above individual execution routing decisions.

Official rule:

- quota applies at user/workspace/system scopes
- quota evaluation occurs before launch and, where relevant, during execution
- quota exhaustion must produce explicit engine truth
- quota decisions must remain distinguishable from validation failure and execution failure
- automation and delivery must also respect quota boundaries

In short:

Nexa quota is a governed permission boundary on how much execution may occur.

## 3. Non-Negotiable Boundaries

The following must remain unchanged:

- Node remains the sole execution unit
- dependency-based execution remains the runtime rule
- execution truth remains engine-owned
- UI does not invent quota states
- quota blocking must not be bypassed through alternate launch paths
- single-run budget routing is not a substitute for user/workspace quota policy

This contract may add quota governance,
but it must not redefine canonical execution semantics.

## 4. Quota Lifecycle

Canonical lifecycle:

Quota Scope Resolution
-> Planned Usage Estimation
-> Quota Check
-> Allow / Warn / Block
-> Optional Mid-Run Quota Monitoring
-> Completion Accounting
-> Updated Quota State

## 5. Contract Family Overview

This contract family contains five conceptual layers:

1. Quota Scope Contract
2. Quota Policy Contract
3. Quota Decision Contract
4. Usage Accounting Contract
5. Quota Record Contract

## 6. Quota Scope Contract

### 6.1 Purpose
Quota scope defines whose allowance is being evaluated.

### 6.2 Canonical quota scope object

QuotaScope
- scope_type: enum("user", "workspace", "organization", "system")
- scope_ref: string
- parent_scope_refs: list[string]

### 6.3 Rules
- quota scope must be explicit
- multiple scopes may apply simultaneously
- stricter blocking scope must win if scopes conflict

## 7. Quota Policy Contract

### 7.1 Purpose
Quota policy defines limit types and thresholds.

### 7.2 Canonical quota policy object

QuotaPolicy
- policy_id: string
- scope_ref: string
- period_type: enum("hour", "day", "week", "month", "rolling_window")
- max_run_count: optional int
- max_estimated_cost: optional float
- max_actual_cost: optional float
- max_stream_minutes: optional float
- max_automation_launches: optional int
- max_delivery_actions: optional int
- warning_threshold_ratio: optional float
- hard_block_enabled: bool

### 7.3 Rules
- quota policy must be explicit and machine-checkable
- warning thresholds must remain separate from hard blocks
- missing quota policy must not be misreported as unlimited unless system policy says so

## 8. Quota Decision Contract

### 8.1 Purpose
Quota decisions determine whether a requested action may proceed.

### 8.2 Canonical quota decision object

QuotaDecision
- decision_id: string
- scope_ref: string
- requested_action_type: enum(
    "run_launch",
    "automation_launch",
    "delivery_action",
    "streaming_continuation",
    "other"
  )
- estimated_usage: optional object
- overall_status: enum("allow", "allow_with_warning", "blocked")
- blocking_reason_code: optional string
- warning_summary: optional string

### 8.3 Rules
- blocked means action must not proceed
- allow_with_warning must remain distinct from blocked
- quota reason codes must remain separate from validation or execution reason codes

## 9. Usage Accounting Contract

### 9.1 Purpose
Quota only works if usage is recorded after the fact.

### 9.2 Canonical usage accounting object

UsageAccountingRecord
- accounting_id: string
- scope_ref: string
- run_ref: optional string
- action_type: string
- estimated_cost: optional float
- actual_cost: optional float
- stream_minutes_used: optional float
- delivery_actions_used: optional int
- automation_launches_used: optional int
- recorded_at: string

### 9.3 Rules
- actual accounting must remain distinguishable from estimate
- failed runs may still consume quota depending on policy
- cancelled or blocked actions must have explicit accounting rules, not hidden assumptions

## 10. Quota Record Contract

### 10.1 Purpose
Quota state must remain inspectable over time.

### 10.2 Canonical quota record object

QuotaStateRecord
- scope_ref: string
- period_ref: string
- consumed_run_count: int
- consumed_estimated_cost: optional float
- consumed_actual_cost: optional float
- consumed_stream_minutes: optional float
- consumed_automation_launches: optional int
- consumed_delivery_actions: optional int
- remaining_summary: optional object
- last_updated_at: string

### 10.3 Rules
- quota records must be period-aware
- remaining state must be derivable or recordable
- scope-level quota history must be auditable

## 11. Pre-Launch and Mid-Run Quota

Quota should operate at two levels where applicable:

### 11.1 Pre-launch
- check estimated usage
- block obvious over-limit launches
- warn when near threshold

### 11.2 Mid-run
- monitor actual usage where needed
- allow cancellation/stop when hard quota breach occurs
- record the reason distinctly from execution failure

Mid-run quota enforcement must remain explicit if used.
It must not look like arbitrary runtime instability.

## 12. Relationship to Budget Routing

Budget routing inside a run and quota governance above a run are related but not identical.

Budget routing answers:
- which provider/model path should this run take?

Quota governance answers:
- may this run happen at all, at this scope, under current allowance?

Both should compose,
but neither replaces the other.

## 13. Relationship to Automation, Streaming, and Delivery

This contract must remain compatible with:
- automation trigger/delivery flows
- execution streaming
- output destination delivery
- provider cost estimation and actual usage accounting

Quota must be enforceable across those paths consistently.

## 14. Explicit Non-Goals

This v1 contract does not define:
- pricing page design
- billing invoice structures
- external payment processing
- organization-role administration UX
- UI rendering implementation details

## 15. Final Statement

Usage quota in Nexa must be an explicit governance boundary.

A user or workspace exceeding safe allowance must be blocked or warned by structured engine truth,
not surprised later by invisible overuse.