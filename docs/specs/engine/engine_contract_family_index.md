# Engine Contract Family Index v0.1

## Recommended save path
`docs/specs/engine/engine_contract_family_index.md`

## 1. Purpose

This document is the official index for Nexa engine-facing contracts that sit outside the basic architecture and storage/UI/plugin bundles.

Its purpose is to reorganize scattered engine contracts into one readable family map so that future implementation work does not confuse:

- active core semantics
- active governed execution contracts
- pending platform-strengthening proposals
- deferred architecture-shift proposals

This index does not replace the underlying contracts.
It routes readers to the correct contract and status.

## 2. Core Classification Rule

Every engine-facing contract in this family must be classified as one of:

1. Active core semantic contract
2. Active governed execution contract
3. Pending platform-strengthening contract
4. Deferred architecture-shift contract
5. Reorganization / index document

Do not infer implementation priority from file existence.

## 3. Active Core Semantic Contracts

These contracts define current engine semantics or current interpretive rules.

| Contract | Path | Role |
|---|---|---|
| Execution Model | `docs/specs/architecture/execution_model.md` | current scheduler/reachability/event semantics |
| Node Execution Contract | `docs/specs/architecture/node_execution_contract.md` | node-bounded execution behavior |
| Circuit Contract | `docs/specs/architecture/circuit_contract.md` | circuit definition and orchestration boundary |
| Validation Engine Contract | `docs/specs/contracts/validation_engine_contract.md` | validation result and execution-blocking rules |
| Validation Rule Catalog | `docs/specs/policies/validation_rule_catalog.md` | stable validation rule ids |
| Circuit Graph Control Flow Contract | `docs/specs/execution/circuit_graph_control_flow_contract.md` | DAG/fan-out/fan-in/cycle/branch/loop interpretation |

## 4. Active Governed Execution Contracts

These are product-grade execution governance contracts.
They belong together and must be implemented as a composed runtime family.

| Contract | Path | Role |
|---|---|---|
| Stage 1 Engine Contract Index | `docs/specs/engine/stage1_engine_contract_index.md` | Stage 1 bundle routing |
| Execution Governance Integration Contract | `docs/specs/engine/execution_governance_integration_contract.md` | cross-contract runtime lifecycle |
| Reason Code Status Taxonomy Contract | `docs/specs/engine/reason_code_status_taxonomy_contract.md` | shared machine-readable status vocabulary |
| Automation Trigger / Delivery Contract | `docs/specs/automation/automation_trigger_delivery_contract.md` | launch and delivery automation lifecycle |
| Execution Streaming Contract | `docs/specs/execution/execution_streaming_contract.md` | truthful incremental execution projection |
| Output Destination Contract | `docs/specs/automation/output_destination_contract.md` | governed external delivery |
| Input Safety Contract | `docs/specs/safety/input_safety_contract.md` | pre-launch safety gate |
| Usage Quota Contract | `docs/specs/governance/usage_quota_contract.md` | quota decision and accounting |

## 5. Pending Platform-Strengthening Contracts

These are useful future contracts that strengthen the platform but do not redefine the core execution constitution.

| Contract | Path | Status |
|---|---|---|
| Batch Execution Contract | `docs/specs/engine/batch_execution_contract.md` | pending / planned |
| Evaluation Node Contract | `docs/specs/engine/evaluation_node_contract.md` | pending / planned |
| Regression Alert Automation Contract | `docs/specs/engine/regression_alert_automation_contract.md` | pending / planned |

Pending does not mean immediate.
Pending means preserved for later product/platform strengthening.

## 6. Deferred Architecture-Shift Contracts

These documents preserve important future design areas that would change execution meaning if implemented prematurely.

| Contract | Path | Status |
|---|---|---|
| Conditional Branch and Loop Node Family | `docs/specs/engine/conditional_branch_loop_node_family.md` | deferred |
| Conditional Branch Node Deferred Contract | `docs/specs/engine/conditional_branch_node_deferred_contract.md` | deferred |
| Loop Node Deferred Contract | `docs/specs/engine/loop_node_deferred_contract.md` | deferred |
| Loop Streaming Output Deferred Contract | `docs/specs/engine/loop_streaming_output_deferred_contract.md` | deferred |
| Dynamic Graph Mutation Deferred Contract | `docs/specs/engine/dynamic_graph_mutation_deferred_contract.md` | deferred / prohibited currently |
| Cross-Run Memory Contract | `docs/specs/engine/cross_run_memory_contract.md` | deferred |
| Interactive Conversational Execution Contract | `docs/specs/engine/interactive_conversational_execution_contract.md` | deferred |

Deferred means:

- not active implementation scope
- not enabled by default
- not to be inferred from ordinary graph or edge semantics
- requires explicit reopening and promotion criteria

## 7. Reorganization Documents

| Document | Path | Role |
|---|---|---|
| Engine Contract Family Index | `docs/specs/engine/engine_contract_family_index.md` | family-level routing |
| Engine Contract Reorganization Map | `docs/specs/engine/engine_contract_reorganization_map.md` | migration / reading-order map |
| Engine Proposals Deferred and Pending | `docs/specs/engine/engine_proposals_deferred_and_pending.md` | proposal holding register |

## 8. Reading Order

Recommended read order for control-flow questions:

1. `architecture/execution_model.md`
2. `execution/circuit_graph_control_flow_contract.md`
3. `contracts/validation_engine_contract.md`
4. `policies/validation_rule_catalog.md`
5. `engine/conditional_branch_loop_node_family.md`
6. deferred branch/loop documents only if future expansion is being considered

Recommended read order for governed runtime questions:

1. `engine/stage1_engine_contract_index.md`
2. `engine/execution_governance_integration_contract.md`
3. automation / streaming / safety / quota / delivery contracts
4. `engine/reason_code_status_taxonomy_contract.md`

## 9. Non-Confusion Rules

1. A document under `docs/specs/engine/` is not automatically active implementation scope.
2. A deferred document is not permission to implement the feature now.
3. A pending document is not a productization blocker unless a later implementation plan promotes it.
4. Structural fan-out is not ConditionalBranchNode.
5. Raw cycle is not LoopNode.
6. Dynamic mutation is not Designer patch/commit.
7. Evaluation is evidence, not approval authority.
8. Regression detection is not automatic notification.
9. Cross-run memory is not run-local context.
10. Conversational execution is not ordinary pause/resume.

## 10. Final Statement

The engine contract family must be read as a status-aware map.

The current core remains:

- Node as sole execution unit
- dependency-based DAG execution
- append-only artifact truth
- trace as first-class execution evidence
- validation before node execution
- no raw cycles
- no hidden runtime graph mutation

The deferred documents preserve future work without weakening current runtime discipline.
