# Circuit Graph Control Flow Contract v0.1

## Recommended save path
`docs/specs/execution/circuit_graph_control_flow_contract.md`

## 1. Purpose

This document defines the canonical graph-level control-flow semantics for Nexa circuits.

Its purpose is to make the following points explicit and enforceable:

- a circuit is not limited to a linear pipeline
- structural fan-out is allowed
- dependency fan-in is allowed
- the default executable circuit graph is a DAG
- raw graph cycles are invalid
- future conditional branch and loop support must be explicit, bounded, traceable, and replay-compatible

This document consolidates control-flow rules that were previously scattered across execution, validation, subcircuit, and deferred-engine documents.

## 2. Core Decision

Nexa circuits are directed dependency graphs.

Official rule:

- Circuit is a connection structure.
- Node remains the sole execution unit.
- Execution is dependency-based, not a fixed linear pipeline.
- The default valid circuit graph is a directed acyclic graph.
- Multiple outgoing edges from one node are allowed.
- Multiple incoming edges into one node are allowed.
- Raw cycles are forbidden.
- Loops must be represented only by future explicit loop contracts.

In short:

Nexa supports graph-shaped execution, but not arbitrary cyclic execution.

## 3. Scope

This contract covers:

- structural branch semantics
- dependency merge semantics
- edge semantics
- scheduler readiness rules
- deterministic ordering rules
- cycle policy
- conditional branch policy
- loop policy
- subcircuit interaction
- trace and artifact expectations
- validation rule anchors

This contract does not implement new runtime behavior by itself.
It defines the official interpretation that validators, schedulers, savefile loaders, Designer AI, and future AI assistants must follow.

## 4. Definitions

### 4.1 Node

A Node is the sole runtime execution unit.

Resources may execute inside a node, but the parent circuit scheduler schedules nodes.

### 4.2 Circuit

A Circuit is a directed connection structure over nodes.

A Circuit is not itself an execution unit.

### 4.3 Edge

An Edge declares a directed dependency from a source node to a target node.

Minimum semantic form:

    source node output may be needed before target node readiness can be evaluated

### 4.4 Structural branch

Structural branch means one node has multiple downstream dependents.

Example:

    A -> B
    A -> C

This is fan-out.
It is allowed.
It does not by itself mean conditional execution.

### 4.5 Dependency merge

Dependency merge means one node has multiple upstream dependencies.

Example:

    B -> D
    C -> D

This is fan-in.
It is allowed.
It does not by itself define aggregation logic.

### 4.6 Conditional branch

Conditional branch means runtime selection among alternative downstream paths based on an explicit decision condition.

This is not the same as structural fan-out.
Explicit conditional branch node semantics are deferred.

### 4.7 Loop

Loop means repeated execution of a bounded body until a termination rule is reached.

Loop semantics must not be represented by raw cyclic graph edges in the base circuit graph.
Explicit loop node semantics are deferred.

### 4.8 Raw cycle

A raw cycle is a graph cycle created by ordinary dependency edges.

Example:

    A -> B -> C -> A

Raw cycles are invalid.

## 5. Default Graph Model

The default valid Nexa circuit graph is a DAG.

Allowed:

    A -> B -> C

Allowed:

          -> B ->
    A ---       ---> D
          -> C ->

Forbidden:

    A -> B -> C
    ^         |
    |---------|

The forbidden form must be rejected during structural validation before node execution.

## 6. Structural Branch Semantics

Structural fan-out is allowed.

When a node has multiple outgoing edges:

1. The source node executes once per run unless another contract explicitly defines otherwise.
2. The source node output may be consumed by multiple downstream nodes.
3. The outgoing edges do not imply priority, condition selection, or exclusive choice unless a separate explicit contract says so.
4. All downstream nodes evaluate readiness according to their own dependency policy.
5. Trace must make it possible to see which downstream nodes became reached, skipped, or blocked.

Structural fan-out is therefore not a loop and not a conditional branch.

## 7. Dependency Merge Semantics

Fan-in is allowed.

When a node has multiple incoming edges:

1. The target node readiness is evaluated according to its flow policy.
2. The target node must not silently execute before its required dependency policy is satisfied.
3. The target node may aggregate upstream outputs only through node-owned execution logic or declared input mapping.
4. Edge structure alone does not define voting, ranking, selection, or synthesis semantics.
5. Trace must make it possible to see which upstream dependencies contributed to readiness.

In short:

- fan-in is a dependency shape
- aggregation is node logic

They must not be confused.

## 8. Current Flow Policy Compatibility

The current execution model already supports bounded reachability policies such as:

- ALL_SUCCESS
- ANY_SUCCESS
- FIRST_SUCCESS

These policies determine whether a target node is ready or skipped based on parent node status.

Important interpretation:

- ALL_SUCCESS is a dependency merge policy.
- ANY_SUCCESS and FIRST_SUCCESS are reachability policies.
- FIRST_SUCCESS in the current v1 deterministic semantics must not be interpreted as a full conditional-branch node family.
- Existing conditional edge or flow gating behavior is bounded reachability logic, not permission for arbitrary runtime graph mutation.

## 9. Scheduler Readiness Rules

A scheduler must treat each non-entry node as pending until readiness can be decided.

Minimum readiness model:

1. Entry node may run when external launch and validation gates permit it.
2. A downstream node may run only when its flow policy is satisfied.
3. A downstream node becomes skipped only when its flow policy can no longer be satisfied by terminal upstream statuses.
4. Pending upstream nodes must not be treated as failure.
5. Failure propagation is a consequence of flow policy, not an independent hidden edge type.

## 10. Deterministic Ordering Rules

When more than one node is ready at the same time, runtime must use deterministic ordering unless a future parallel execution contract explicitly changes that behavior.

Minimum deterministic ordering rule:

1. topological readiness before execution order
2. stable tie-breaker among concurrently ready nodes
3. tie-breaker should be stable across replay, for example canonical node id order
4. trace must record actual execution order

Parallel execution, if later introduced, must not erase deterministic replay requirements.

## 11. Cycle Policy

Raw graph cycles are forbidden.

Official validation anchor:

- rule id: ENG-003
- meaning: Engine graph must be a DAG
- severity: error
- effect: node execution must be rejected

Additional future validator aliases may include:

- GRAPH_CYCLE_FORBIDDEN
- RAW_GRAPH_CYCLE_FORBIDDEN

These aliases may exist as human-readable names, but stable machine-readable rule ids must remain governed by the validation rule catalog.

## 12. Conditional Branch Policy

Structural fan-out is currently allowed.

Explicit conditional branch nodes are deferred.

Current rule:

- ordinary multiple outgoing edges are structural fan-out
- they do not mean exclusive conditional selection
- conditional branch behavior must not be inferred from edge shape alone
- future conditional branch support must be represented by an explicit contract family

Future explicit branch support must define at least:

- branch decision object
- decision input binding
- branch predicate language or decision source
- branch priority and default branch rules
- branch decision trace record
- skipped-path representation
- replay semantics
- validation rules

## 13. Loop Policy

Raw cycles are not loops.

Current rule:

- ordinary graph cycles are invalid
- loop behavior is unsupported in the base graph model
- future loop support must be explicit, bounded, traceable, quota-aware, and replay-compatible

Future loop support must define at least:

- loop body boundary
- max iteration policy
- termination policy
- state carry policy
- per-iteration trace policy
- per-iteration artifact policy
- timeout and quota policy
- failure and partial-result policy
- replay semantics

## 14. Subcircuit Interaction

SubcircuitNode does not change the base graph control-flow rule.

Official interpretation:

1. A SubcircuitNode is a node-kind in the parent circuit.
2. The parent graph sees the SubcircuitNode as one node.
3. The child circuit executes inside the SubcircuitNode boundary.
4. Parent-child data exchange occurs only through explicit input mapping and output binding.
5. Direct parent/child context sharing is forbidden.
6. Recursive self-reference and multi-step cyclic subcircuit references are invalid unless a future explicit recursion contract exists.

SubcircuitNode may contain fan-out and fan-in inside the child circuit, but it must still obey the same DAG default unless future explicit loop semantics are introduced.

## 15. Trace Semantics

Trace must preserve graph-control observability.

Minimum trace expectations:

- node reached / not reached / skipped / failed status
- execution order
- upstream readiness cause where available
- flow policy result where available
- branch/loop decision records only when future explicit branch/loop contracts exist
- subcircuit parent/child linkage where SubcircuitNode is used

Trace must not pretend that a branch or loop occurred when only structural fan-out or fan-in occurred.

## 16. Artifact Semantics

Graph control-flow must preserve artifact truth.

Rules:

1. Artifacts are append-only.
2. Multiple downstream consumers may read a source artifact without mutating it.
3. Merge nodes may produce new artifacts, but must not rewrite upstream artifacts.
4. Future loop iterations must use iteration-scoped artifact identity if loop support is introduced.
5. Future branch decisions may produce branch-decision artifacts, but those artifacts are evidence, not hidden graph mutation.

## 17. Validation Rules

Current and planned validation anchors:

| Rule | Alias (non-authoritative) | Status | Severity | Meaning |
|---|---|---|---:|---|
| ENG-003 | GRAPH_CYCLE_FORBIDDEN, RAW_GRAPH_CYCLE_FORBIDDEN | active | error | raw graph cycle / DAG violation |
| CH-001 | EDGE_TARGET_MISSING, EDGE_SOURCE_MISSING | active | error | edge/channel references missing node |
| FLOW-001 | FLOW_REFERENCE_MISSING_NODE | active/planned | error | flow references missing node |
| FLOW-004 | UNREACHABLE_NODE | active/planned | warning | unreachable node detected |
| FLOW-005 | DEAD_BRANCH | active/planned | warning | dead branch detected |
| FLOW-006 | CONDITIONAL_BRANCH_NODE_UNSUPPORTED | planned | error | unsupported conditional branch node used as executable feature |
| FLOW-007 | LOOP_NODE_UNSUPPORTED | planned | error | unsupported loop node used as executable feature |
| FLOW-008 | AMBIGUOUS_OUTPUT_BINDING | planned | error | ambiguous output binding across fan-in |
| FLOW-016 | MERGE_REQUIRES_ALL_REQUIRED_INPUTS | reserved | error | dependency merge missing required upstream inputs |
| FLOW-017 | UNDECLARED_OPTIONAL_DEPENDENCY | reserved | warning | optional upstream dependency consumed without declaration |
| ENG-004 | DYNAMIC_STRUCTURE_MUTATION_DETECTED | active/planned | error | dynamic structure mutation declared/detected |

Where the validation rule catalog already defines a stable id, that id remains authoritative.
Human-readable aliases may be used in UI or documentation, but not as replacements for stable rule ids.

## 18. Savefile Examples

### 18.1 Structural fan-out

    nodes:
      - node_id: a
      - node_id: b
      - node_id: c
    edges:
      - from: a
        to: b
      - from: a
        to: c

Interpretation:

- A executes once.
- B and C may both become ready after A depending on policy.
- This is not conditional branching.

### 18.2 Dependency fan-in

    nodes:
      - node_id: b
      - node_id: c
      - node_id: d
    edges:
      - from: b
        to: d
      - from: c
        to: d

Interpretation:

- D has two upstream dependencies.
- D readiness depends on its flow policy.
- D aggregation behavior belongs to D's node logic, not the edge itself.

### 18.3 Invalid raw cycle

    edges:
      - from: a
        to: b
      - from: b
        to: c
      - from: c
        to: a

Interpretation:

- Invalid.
- Structural validation must reject before node execution.

## 19. Non-Goals

This document does not define:

- full ConditionalBranchNode implementation
- full LoopNode implementation
- streaming loop output implementation
- cross-run loop memory
- runtime graph mutation
- autonomous graph rewrite
- distributed graph execution
- parallel scheduler semantics

Those are preserved in deferred engine contracts and must not be silently inferred from this document.

## 20. Final Statement

Nexa circuits are graph-shaped, not merely linear.

The official baseline is:

- structural branch: allowed
- dependency merge: allowed
- raw cycle: forbidden
- conditional branch: deferred explicit control node family
- loop: deferred explicit bounded loop family
- dynamic graph mutation: forbidden unless later reopened under a separate contract

This keeps Nexa expressive enough for non-linear workflows while preserving traceability, replayability, validation, and auditability.
