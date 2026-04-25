# Engine Contract Reorganization Map v0.1

## Recommended save path
`docs/specs/engine/engine_contract_reorganization_map.md`

## 1. Purpose

This document records the reorganization of Nexa's scattered engine contracts into a clearer contract family.

It answers:

- which documents are active
- which documents are pending
- which documents are deferred
- which document answers which engine-control question
- how future AI assistants should navigate the engine spec set

## 2. Reorganization Summary

The reorganization adds one active control-flow contract and expands deferred control-flow preservation documents.

New or expanded documents:

- `docs/specs/execution/circuit_graph_control_flow_contract.md`
- `docs/specs/engine/conditional_branch_loop_node_family.md`
- `docs/specs/engine/conditional_branch_node_deferred_contract.md`
- `docs/specs/engine/loop_node_deferred_contract.md`
- `docs/specs/engine/loop_streaming_output_deferred_contract.md`
- `docs/specs/engine/dynamic_graph_mutation_deferred_contract.md`
- `docs/specs/engine/engine_contract_family_index.md`
- `docs/specs/engine/engine_contract_reorganization_map.md`

## 3. Why This Reorganization Was Needed

Before this reorganization, important engine rules were spread across:

- execution model
- circuit contract
- validation contract
- validation rule catalog
- subcircuit contract
- Stage 1 governance contracts
- short deferred proposal stubs

This created ambiguity around questions such as:

- Is a Nexa circuit linear?
- Are fan-out and fan-in allowed?
- Are raw cycles allowed?
- Is a loop just a cyclic edge?
- Is conditional branching already implied by multiple outgoing edges?
- Does future branch/loop support require new validation and trace contracts?
- Are deferred engine proposals implementation permission?

The new organization answers those directly.

## 4. Current Canonical Answers

| Question | Canonical answer | Primary document |
|---|---|---|
| Is Nexa linear only? | No. It is a directed dependency graph. | `circuit_graph_control_flow_contract.md` |
| Is fan-out allowed? | Yes, as structural branch. | `circuit_graph_control_flow_contract.md` |
| Is fan-in allowed? | Yes, as dependency merge. | `circuit_graph_control_flow_contract.md` |
| Are raw cycles allowed? | No. DAG violation. | `circuit_graph_control_flow_contract.md`, `validation_rule_catalog.md` |
| Is ConditionalBranchNode active? | No. Deferred. | `conditional_branch_node_deferred_contract.md` |
| Is LoopNode active? | No. Deferred. | `loop_node_deferred_contract.md` |
| Is loop streaming defined? | Preserved as deferred policy. | `loop_streaming_output_deferred_contract.md` |
| Is runtime graph mutation allowed? | No. Currently prohibited. | `dynamic_graph_mutation_deferred_contract.md` |
| Are pending/deferred docs implementation scope? | No. They are status-tagged preservation docs. | `engine_contract_family_index.md` |

## 5. Placement Rules

### 5.1 Active core semantics

Put active semantics under the closest existing family:

- `docs/specs/architecture/` for core architecture
- `docs/specs/execution/` for execution behavior
- `docs/specs/contracts/` for cross-cutting contracts
- `docs/specs/policies/` for validation/status rule catalogs

### 5.2 Engine expansion / proposal family

Put engine-expansion proposals under:

- `docs/specs/engine/`

Then clearly mark each document:

- active
- pending
- deferred
- prohibited currently

### 5.3 Indexes

Use:

- `docs/specs/engine/engine_contract_family_index.md` for engine-family routing
- `docs/specs/indexes/spec_catalog.md` for overall spec catalog
- `docs/specs/indexes/spec_dependency_map.md` for dependency relationships
- `docs/INDEX.md` for human-facing documentation discovery

## 6. Migration Notes

### 6.1 `conditional_branch_loop_node_family.md`

Previously a short deferred note.
Now expanded into a family-level deferred contract.

### 6.2 `circuit_graph_control_flow_contract.md`

New active reference contract.
It clarifies current graph semantics without adding new runtime behavior.

### 6.3 `dynamic_graph_mutation_deferred_contract.md`

New deferred/prohibited-current contract.
It prevents future accidental runtime graph mutation.

### 6.4 `loop_streaming_output_deferred_contract.md`

New preservation contract.
It records the future streaming-loop policy so that loop support is not implemented without partial/final boundaries.

## 7. What Must Not Be Misread

1. Deferred docs are not build tickets.
2. Raw cycles remain invalid.
3. LoopNode is not implemented by ordinary cyclic edges.
4. ConditionalBranchNode is not implemented by ordinary fan-out.
5. Dynamic mutation is not authorized by Designer AI.
6. Streaming loop output is not ordinary provider streaming repeated several times.
7. Engine docs do not override storage/UI/plugin truth boundaries.

## 8. Future Promotion Procedure

To promote a deferred engine contract:

1. create an explicit promotion decision document
2. update `engine_contract_family_index.md`
3. update `engine_proposals_deferred_and_pending.md`
4. update `spec_catalog.md`
5. update `spec_dependency_map.md`
6. add validator rules or rule-catalog entries
7. add implementation tests
8. add replay/audit evidence tests where applicable
9. update UI projection only after engine truth exists

## 9. Final Statement

This reorganization keeps Nexa from losing future design ideas while preserving current execution discipline.

The engine is now documented as:

- graph-shaped but DAG-bounded today
- branch/merge capable today at structural/dependency level
- explicit branch/loop capable only in deferred future contracts
- mutation-resistant unless later reopened under strict governance
