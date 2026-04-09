# Execution Governance Integration Contract

## Recommended save path
`docs/specs/engine/execution_governance_integration_contract.md`

## 1. Purpose

This document defines how execution, automation, streaming, input safety, output delivery, and usage quota integrate as one coherent engine flow in Nexa.

Its purpose is to prevent subsystem-level contracts from being implemented correctly in isolation but incorrectly in combination.

This contract exists because product-grade engine behavior depends on composition, not only on local correctness.

## 2. Core Decision

All Stage 1 governance contracts must compose into one canonical runtime lifecycle.

Official rule:

- automation may request launch, but cannot bypass safety or quota
- safety may block launch before execution starts
- quota may block launch or continuation without masquerading as validation failure
- streaming may expose truthful incremental state, but cannot fabricate completion
- delivery may occur only after explicit result selection and destination authorization
- all outcomes must remain traceable under one run identity

In short:

Nexa must behave as one governed runtime, not as five disconnected subsystems.

## 3. Canonical Integrated Lifecycle

Canonical lifecycle:

Trigger / User Action
-> Launch Request
-> Input Safety Evaluation
-> Quota Evaluation
-> Launch Allow / Block Decision
-> Execution Start
-> Streaming / Event Emission
-> Execution Completion / Failure / Cancellation
-> Result Selection
-> Destination Delivery Evaluation
-> Delivery Attempt / Retry
-> Final Records and Accounting Update

## 4. Integration Boundaries

### 4.1 Launch Boundary
Before a run starts, the engine must determine:
- who requested the run
- under what trigger/source
- what input is entering execution
- whether quota allows the run
- whether launch is blocked, warned, or allowed

### 4.2 Runtime Boundary
Once running, the engine may:
- emit streaming events
- update progress
- produce artifacts
- accumulate actual usage
- optionally enforce mid-run quota rules if configured

### 4.3 Post-Run Boundary
After execution, the engine must separate:
- execution result
- delivery result
- safety record
- quota accounting record
- historical run truth

These must not be collapsed into one status.

## 5. Canonical Status Families

The engine must maintain distinct status families.

### 5.1 Launch Status
- requested
- safety_blocked
- quota_blocked
- allowed
- confirmation_required
- launch_cancelled

### 5.2 Execution Status
- queued
- running
- completed
- failed
- cancelled
- partial

### 5.3 Delivery Status
- not_attempted
- pending
- sending
- succeeded
- failed
- blocked
- cancelled

### 5.4 Governance Status
- within_quota
- near_quota
- over_quota_blocked
- input_safe
- input_warning
- input_blocked
- confirmation_required

Rules:
- UI may summarize these together, but engine must store them separately
- execution completion must not imply delivery success
- safety block must not be mislabeled as run failure
- quota block must not be mislabeled as validation error

## 6. Required Shared References

All subsystems must be able to reference a shared identity spine.

Minimum shared references:
- run_ref
- launch_request_ref
- trigger_ref (optional where relevant)
- safety_decision_ref
- quota_decision_ref
- execution_record_ref
- selected_output_ref / selected_artifact_ref
- delivery_plan_ref
- delivery_attempt_ref
- accounting_ref

## 7. Policy Resolution Order

Minimum recommended decision order:

1. Resolve launch source/context
2. Resolve input set
3. Evaluate input safety
4. Evaluate quota
5. Produce launch decision
6. If allowed, start execution
7. If completed, evaluate result selection and destination delivery
8. Record delivery and accounting outcomes

This order prevents late discovery of obvious pre-launch blocks.

## 8. Failure Semantics

The engine must support the following distinctions:

### 8.1 Safety-blocked, no run started
No execution started.
This is not a failed run.

### 8.2 Quota-blocked, no run started
No execution started.
This is not a failed run.

### 8.3 Run failed before any deliverable result
Execution failure.
Delivery remains not_attempted.

### 8.4 Run completed, delivery blocked
Execution success may coexist with delivery blocked.

### 8.5 Run completed, delivery failed
Execution success may coexist with delivery failure.

### 8.6 Run cancelled mid-way
Execution cancellation may still generate partial artifacts, depending on runtime policy.

## 9. Streaming Relationship

Streaming is a projection of engine truth during runtime.

Therefore:
- pre-launch safety/quota block states may be emitted as launch events, not fake run-progress events
- partial outputs must remain distinguishable from final outputs
- delivery attempts are downstream operational events, not execution-progress events
- UI must not smooth over category boundaries for convenience

## 10. Accounting Relationship

Accounting must update based on explicit policy.

Minimum distinctions:
- blocked before launch
- launched but failed
- launched and completed
- delivered vs not delivered
- retried delivery attempts

This prevents billing/governance ambiguity later.

## 11. Explicit Non-Goals

This v1 contract does not define:
- concrete UI widget shapes
- organization permissions and reviewer authority
- payment processor integration
- vendor-specific delivery protocol details
- legal retention policies

## 12. Final Statement

Nexa must compose Stage 1 contracts into one coherent governed lifecycle.

Correct local features are insufficient if the integrated runtime still produces ambiguous truth.