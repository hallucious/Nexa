# Automation Trigger / Delivery Contract

## Recommended save path
`docs/specs/automation/automation_trigger_delivery_contract.md`

## 1. Purpose

This document defines the canonical automation contract for Nexa when engine-level contract changes are allowed.

Its purpose is to unify two ends of the same general-user automation flow:

- how an automation run starts
- how its result is delivered outward

This contract exists because, for general users, automation value is rarely created by trigger-only behavior or delivery-only behavior.
The useful flow is usually:

external event or schedule
-> trigger evaluation
-> circuit launch
-> execution
-> result selection
-> delivery to an external destination

This document treats that flow as one coherent engine-facing automation contract.

## 2. Core Decision

Automation trigger and external delivery must be designed as one contract family.

Official rule:

- trigger-side automation and delivery-side automation must share a common run identity
- both must remain traceable as part of one automation lifecycle
- both must respect the same safety, quota, and observability boundaries
- neither may bypass circuit execution truth or artifact truth

In short:

Nexa automation is not merely "start automatically."
It is "start under explicit conditions and deliver under explicit rules."

## 3. Non-Negotiable Boundaries

The following must remain unchanged:

- Node remains the sole execution unit
- dependency-based execution remains the runtime rule
- engine-owned execution truth remains authoritative
- artifact append-only principles remain intact
- storage truth is not redefined by automation
- UI does not fabricate automation truth

This contract may extend the engine with automation capabilities,
but it must not turn Nexa into an unbounded ad hoc event script runner.

## 4. Automation Lifecycle

Canonical lifecycle:

Trigger Source
-> Trigger Evaluation
-> Launch Decision
-> Circuit Execution
-> Result Selection
-> Delivery Decision
-> Delivery Execution
-> Automation Record / Trace

Every automation run must preserve this lifecycle explicitly,
even if some phases are skipped or collapse into defaults.

## 5. Contract Family Overview

This contract family contains five conceptual layers:

1. Trigger Source Contract
2. Launch Policy Contract
3. Delivery Destination Contract
4. Delivery Policy Contract
5. Automation Record / Trace Contract

## 6. Trigger Source Contract

### 6.1 Purpose
A trigger source defines where the automation signal came from.

### 6.2 Initial supported trigger families
Initial engine-facing trigger families may include:

- schedule trigger
- file/input arrival trigger
- webhook/event trigger
- manual replay trigger
- future connector-origin trigger

### 6.3 Canonical trigger object

AutomationTriggerSource
- trigger_id: string
- trigger_type: enum("schedule", "file_arrival", "webhook", "manual_replay", "connector_event")
- source_ref: optional string
- source_metadata: optional object
- owner_scope: optional string
- is_enabled: bool

### 6.4 Rules
- every trigger must have a stable identity
- every trigger must declare its type explicitly
- trigger sources must not directly execute nodes
- trigger source emission and actual circuit launch are separate phases

## 7. Trigger Evaluation Contract

### 7.1 Purpose
Trigger evaluation decides whether an incoming trigger event is sufficient to launch the circuit.

### 7.2 Canonical evaluation object

TriggerEvaluation
- trigger_ref: string
- evaluation_time: string
- matched: bool
- reason_code: string
- condition_summary: optional string
- launch_allowed: bool
- quota_allowed: bool
- safety_allowed: bool
- findings: optional list[object]

### 7.3 Rules
- a trigger event may match but still be blocked by quota or safety policy
- launch decisions must be explainable
- launch must never happen through implicit side effects
- evaluation results must be recordable for audit and debugging

## 8. Launch Policy Contract

### 8.1 Purpose
Launch policy defines how a matched trigger becomes a circuit run.

### 8.2 Canonical launch policy object

AutomationLaunchPolicy
- policy_id: string
- circuit_ref: string
- input_mapping_mode: enum("fixed", "event_bound", "artifact_bound", "template_bound")
- launch_mode: enum("immediate", "queued", "debounced")
- concurrency_mode: enum("single_active", "allow_parallel", "replace_pending")
- failure_mode: enum("stop", "retry", "record_only")
- max_retries: optional int

### 8.3 Rules
- launch policy must name the target circuit explicitly
- trigger event data must be mapped into a bounded input contract
- automation launch must preserve standard execution tracing
- no hidden launch path may bypass normal circuit execution recording

## 9. Delivery Destination Contract

### 9.1 Purpose
Delivery destination defines where execution results may go after the run.

### 9.2 Initial supported destination families
Initial delivery destination families may include:

- email
- Slack / chat destination
- spreadsheet destination
- webhook / HTTP destination
- storage destination
- future connector destination

### 9.3 Canonical destination object

AutomationDeliveryDestination
- destination_id: string
- destination_type: enum("email", "slack", "spreadsheet", "webhook", "storage", "connector")
- target_ref: string
- target_metadata: optional object
- is_enabled: bool

### 9.4 Rules
- destinations must be explicit objects, not hidden plugin side effects
- delivery target identity must be inspectable
- destination configuration must remain separable from core execution truth
- delivery destinations must be subject to permission, safety, and quota constraints

## 10. Delivery Policy Contract

### 10.1 Purpose
Delivery policy decides what is delivered, when it is delivered, and under which conditions.

### 10.2 Canonical delivery policy object

AutomationDeliveryPolicy
- policy_id: string
- destination_ref: string
- delivery_trigger: enum("on_success", "on_failure", "on_completion", "manual_only")
- payload_mode: enum("final_output", "selected_artifact", "summary_only", "digest")
- retry_mode: enum("none", "bounded_retry", "exponential_backoff")
- max_delivery_retries: optional int
- failure_visibility: enum("silent_record", "warn_user", "escalate")
- formatting_profile: optional string

### 10.3 Rules
- delivery must never be ambiguous about which output/artifact is being sent
- delivery policy must distinguish success-path delivery from failure-path delivery
- delivery retries must be bounded
- delivery failure must be traceable separately from core circuit failure

## 11. Automation Record / Trace Contract

### 11.1 Purpose
Automation activity must be inspectable as a first-class execution-related record.

### 11.2 Canonical automation record object

AutomationRunRecord
- automation_run_id: string
- trigger_ref: string
- trigger_event_summary: object
- launch_policy_ref: string
- execution_run_ref: optional string
- delivery_policy_refs: list[string]
- destination_refs: list[string]
- automation_status: enum(
    "trigger_blocked",
    "launch_skipped",
    "launch_started",
    "execution_completed",
    "delivery_partial",
    "delivery_completed",
    "delivery_failed",
    "automation_failed"
  )
- timestamps: object
- findings: optional list[object]

### 11.3 Rules
- automation records must link trigger, execution, and delivery in one inspectable chain
- automation records must not replace execution records
- automation trace must remain compatible with engine trace truth
- a delivery failure after a successful execution must remain distinguishable from execution failure

## 12. Safety and Quota Boundary

### 12.1 Safety boundary
Automation must respect input/content safety policy before launch and before delivery when applicable.

Minimum required checks:
- unsafe input detection
- restricted data handling checks
- destination safety checks
- policy-based block conditions

### 12.2 Quota boundary
Automation must respect user-level or workspace-level quota boundaries.

Minimum required checks:
- launch frequency limit
- delivery frequency limit
- cost ceiling / budget ceiling
- retry explosion prevention

### 12.3 Rule
Trigger evaluation, execution launch, and delivery must all be independently blockable by safety or quota checks.

## 13. UX and Visibility Requirements

Even though this is an engine-facing contract, it must support user-facing visibility.

Minimum UX-visible facts:
- what triggered the run
- whether the run launched
- whether delivery was attempted
- where the result was sent
- whether delivery failed
- what the next corrective action is

This contract must support future beginner-safe surfaces without requiring redefinition of engine truth.

## 14. Initial Prioritization Guidance

For general-user engine expansion, this contract belongs to Stage 1 engine-facing value work.

Within that stage, the recommended paired design direction is:

1. Trigger side and delivery side are specified together
2. execution streaming remains a separate but compatible engine contract
3. safety and quota checks are designed from the start
4. delivery is bounded and explicit, not hidden as uncontrolled plugin write behavior

## 15. Explicit Non-Goals

This v1 contract does not define:

- unrestricted loop automation
- arbitrary conditional orchestration language
- conversational follow-up execution
- cross-run memory semantics
- marketplace/community sharing behavior
- full connector ecosystem details

Those belong to later contracts or later architectural phases.

## 16. Final Statement

Automation in Nexa must be treated as a bounded, traceable lifecycle from trigger to delivery.

The engine must not model trigger and delivery as unrelated conveniences.

For general-user value, they are two ends of one automation contract.