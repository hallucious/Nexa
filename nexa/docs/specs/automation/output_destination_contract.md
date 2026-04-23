# Output Destination Contract

## Recommended save path
`docs/specs/automation/output_destination_contract.md`

## 1. Purpose

This document defines the canonical output-destination contract for Nexa when engine-level contract changes are allowed.

Its purpose is to let circuit results leave Nexa under explicit, traceable, policy-bounded rules.

This contract exists because general-user value often does not end at:
- run completed
- result visible in Nexa

The useful end state is often:
- send result to Slack
- write result to email
- save result to sheet / document / external system
- notify another system with a selected output

Output destination must therefore become an explicit engine contract,
not an ad hoc plugin side effect.

## 2. Core Decision

External delivery must be explicit, selectable, and traceable.

Official rule:

- a delivery target must be declared explicitly
- delivery must be tied to a concrete run identity
- delivery must not bypass execution truth or artifact truth
- delivery must remain policy-bounded, safety-bounded, and quota-aware
- delivery success/failure must become observable engine truth

In short:

Nexa delivery is not "plugin write happened somewhere."
It is a governed result-export action attached to a run.

## 3. Non-Negotiable Boundaries

The following must remain unchanged:

- Node remains the sole execution unit
- dependency-based execution remains the runtime rule
- artifact append-only principles remain intact
- engine-owned execution truth remains authoritative
- UI does not fabricate delivery truth
- destination write must not silently redefine canonical circuit output

This contract may extend external write behavior,
but it must not turn Nexa into an unbounded arbitrary side-effect runner.

## 4. Delivery Lifecycle

Canonical lifecycle:

Execution Completed
-> Result Selection
-> Delivery Plan Resolution
-> Destination Authorization Check
-> Delivery Attempt
-> Delivery Result Recording
-> Delivery Success / Failure / Retry Decision

Delivery must remain downstream of execution truth.
It must never be mistaken for execution itself.

## 5. Contract Family Overview

This contract family contains five conceptual layers:

1. Destination Capability Contract
2. Delivery Plan Contract
3. Delivery Attempt Contract
4. Delivery Record Contract
5. Retry / Failure Policy Contract

## 6. Destination Capability Contract

### 6.1 Purpose
A destination capability contract defines what a destination can receive and how it can be addressed.

### 6.2 Canonical destination capability object

DestinationCapability
- destination_type: enum(
    "email",
    "slack",
    "webhook",
    "document",
    "spreadsheet",
    "storage",
    "other"
  )
- destination_ref: string
- supports_text: bool
- supports_structured_payload: bool
- supports_attachments: bool
- supports_idempotency_key: bool
- supports_retry: bool
- max_payload_policy: optional object
- auth_mode: enum("managed", "user_bound", "service_bound", "unknown")

### 6.3 Rules
- destination capability must be declared explicitly
- unsupported payload shapes must be rejected before delivery attempt
- auth mode must be visible to policy/governance layers
- destinations must not be assumed interchangeable

## 7. Delivery Plan Contract

### 7.1 Purpose
A delivery plan defines what result leaves Nexa, where it goes, and under what conditions.

### 7.2 Canonical delivery plan object

DeliveryPlan
- delivery_plan_id: string
- run_ref: string
- destination_ref: string
- destination_type: string
- selected_output_ref: optional string
- selected_artifact_ref: optional string
- payload_projection_mode: enum(
    "final_output",
    "artifact_ref",
    "artifact_content",
    "summary",
    "custom_projection"
  )
- title_template: optional string
- body_template: optional string
- attachment_refs: list[string]
- requires_confirmation: bool
- safety_scope: optional object
- quota_scope: optional object

### 7.3 Rules
- a delivery plan must point to explicit result sources
- ambiguous "send whatever came out" behavior is invalid
- payload projection mode must preserve result meaning
- destructive delivery-side transformation must not masquerade as canonical output

## 8. Delivery Attempt Contract

### 8.1 Purpose
A delivery attempt records each concrete try to deliver a result outward.

### 8.2 Canonical delivery attempt object

DeliveryAttempt
- attempt_id: string
- delivery_plan_ref: string
- run_ref: string
- destination_ref: string
- started_at: string
- completed_at: optional string
- status: enum(
    "pending",
    "sending",
    "succeeded",
    "failed",
    "cancelled",
    "blocked"
  )
- idempotency_key: optional string
- response_summary: optional object
- failure_reason_code: optional string
- retry_eligible: bool

### 8.3 Rules
- delivery attempts must be individually recorded
- failure must be explicit
- retry eligibility must not be guessed by UI
- idempotency must be supported where possible to prevent duplicate side effects

## 9. Delivery Record Contract

### 9.1 Purpose
Delivery must remain inspectable after the run completes.

### 9.2 Canonical delivery record object

DeliveryRecord
- run_ref: string
- destination_ref: string
- destination_type: string
- selected_output_ref: optional string
- selected_artifact_ref: optional string
- latest_status: enum(
    "not_attempted",
    "succeeded",
    "failed",
    "cancelled",
    "blocked",
    "unknown"
  )
- attempt_refs: list[string]
- delivered_at: optional string
- delivery_summary: optional object

### 9.3 Rules
- delivery records must remain linked to execution history
- success/failure must remain distinguishable from execution success/failure
- result destination must remain inspectable in trace/history

## 10. Retry / Failure Policy Contract

### 10.1 Purpose
Destination failure should not collapse into ambiguous partial success.

### 10.2 Canonical retry policy object

DeliveryRetryPolicy
- destination_type: string
- retry_mode: enum("none", "fixed", "bounded_backoff", "manual_only")
- max_attempts: int
- retry_on_reason_codes: list[string]
- block_on_reason_codes: list[string]

### 10.3 Rules
- retry policy must be explicit
- repeated delivery attempts must not silently duplicate irreversible effects
- manual-only retry must be supported for sensitive destinations

## 11. Output Selection Boundary

Not every execution output should be delivered automatically.

Minimum explicit choices:
- which output
- which artifact
- which projection
- which destination
- whether confirmation is required

The engine must not assume that the most visible output is automatically the correct outbound result.

## 12. Relationship to Automation

This contract is compatible with automation trigger/delivery flow,
but it is independently valid.

Automation answers:
- when should a run start?

Output destination answers:
- what should leave Nexa after the run?

The two should compose cleanly,
but delivery must remain inspectable as its own governed phase.

## 13. Safety and Quota Relationship

This contract must remain compatible with:
- input safety / content safety
- destination-specific safety rules
- user or workspace quota rules
- outbound policy rules

Delivery must be blockable even after execution success if outbound policy rejects the selected result.

## 14. Explicit Non-Goals

This v1 contract does not define:
- collaborative inbox workflows
- human conversation threading at the destination
- cross-run destination memory
- full destination-specific schema mapping for every provider
- UI rendering implementation details

## 15. Final Statement

Output destination in Nexa must be a governed outbound result contract.

A result leaving Nexa is not an invisible plugin side effect.
It is a traceable, policy-bounded, destination-specific delivery action attached to execution truth.