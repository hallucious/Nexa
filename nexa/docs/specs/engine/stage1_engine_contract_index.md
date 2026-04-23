# Stage 1 Engine Contract Index

## Recommended save path
`docs/specs/engine/stage1_engine_contract_index.md`

## 1. Purpose

This document is the official index for the Stage 1 engine-facing contract bundle in Nexa.

Its purpose is to:
- define the canonical Stage 1 contract set
- explain why these contracts belong together
- clarify reading order
- clarify implementation dependency order
- reduce drift between automation, execution, safety, delivery, and governance work

Stage 1 here means:
the minimum contract layer required to make Nexa behave like a governed product-grade execution engine,
not merely a local experiment runner.

## 2. Why This Index Exists

The Stage 1 contracts are tightly connected.

If they are implemented independently without a shared map, common failure modes appear:
- automation starts runs that quota should have blocked
- delivery happens without explicit output selection
- safety findings are confused with validation or execution failure
- streaming appears in UI without engine-owned truth
- reason codes diverge across subsystems

This index exists to stop that drift.

## 3. Canonical Stage 1 Contract Bundle

The canonical Stage 1 bundle currently contains five contracts.

### 3.1 Automation Trigger / Delivery Contract
Path:
`docs/specs/automation/automation_trigger_delivery_contract.md`

Role:
- defines how automation launches runs
- defines automation lifecycle identity
- defines delivery as part of automation lifecycle
- keeps trigger/delivery tied to execution truth

### 3.2 Execution Streaming Contract
Path:
`docs/specs/execution/execution_streaming_contract.md`

Role:
- defines truthful real-time execution projection
- distinguishes partial vs final output
- keeps streaming engine-originated, not UI-fabricated

### 3.3 Output Destination Contract
Path:
`docs/specs/automation/output_destination_contract.md`

Role:
- defines governed outbound result delivery
- defines destination capability, delivery plan, attempt, record, retry policy
- prevents delivery from becoming hidden plugin side effects

### 3.4 Input Safety Contract
Path:
`docs/specs/safety/input_safety_contract.md`

Role:
- defines pre-execution input gate
- defines structured safety findings and launch decisions
- prevents unsafe input from silently entering execution

### 3.5 Usage Quota Contract
Path:
`docs/specs/governance/usage_quota_contract.md`

Role:
- defines quota scope, policy, decision, accounting, and historical record
- prevents invisible overuse and uncontrolled automation cost

## 4. Reading Order

Recommended reading order:

1. `automation_trigger_delivery_contract.md`
2. `execution_streaming_contract.md`
3. `output_destination_contract.md`
4. `input_safety_contract.md`
5. `usage_quota_contract.md`

Reason:
- first understand when a run may start
- then understand what execution may reveal while running
- then understand what may leave the system
- then understand what must be blocked before launch
- then understand how all of that is bounded over time

## 5. Implementation Dependency Order

Recommended implementation order:

### Step 1
Execution identity + automation launch anchor

### Step 2
Streaming/event projection

### Step 3
Input safety pre-launch gate

### Step 4
Quota pre-launch and post-run accounting

### Step 5
Explicit output selection and destination delivery

### Step 6
Cross-contract reason code alignment

### Step 7
UI/view-model integration

## 6. Cross-Contract Invariants

The following must remain true across all Stage 1 contracts:

1. Node remains the sole execution unit
2. Dependency-based execution remains the runtime rule
3. Engine-owned execution truth remains authoritative
4. Artifact append-only principles remain intact
5. UI may render but must not fabricate truth
6. Safety, quota, delivery, streaming, and automation states must remain distinguishable
7. Reason codes must be machine-usable and subsystem-stable

## 7. What Stage 1 Does Not Yet Cover

This Stage 1 bundle does not yet fully define:
- organization administration workflows
- billing/invoicing surfaces
- destination-specific vendor schema mapping in depth
- collaboration review authority workflows
- full compliance framework by jurisdiction
- end-user SaaS account systems

## 8. Final Statement

Stage 1 in Nexa is the minimum governed execution layer.

These contracts must be read and implemented as one connected system,
not as isolated convenience features.