# Conditional Branch and Loop Node Family v0.2

## Recommended save path
`docs/specs/engine/conditional_branch_loop_node_family.md`

## 1. Status

Deferred architecture-shift contract family.

This document preserves the future design space for explicit conditional branching and looping.
It does not authorize immediate implementation.

## 2. Purpose

This document defines the future contract family for explicit conditional branching and explicit looping in Nexa.

It exists because the base control-flow contract intentionally permits structural fan-out and fan-in, but forbids raw graph cycles and defers richer control-flow semantics.

The goal is to prevent future implementers from treating branch and loop support as a quick edge-level change.

## 3. Core Decision

Future branch and loop support must be explicit, node-bounded, traceable, replay-compatible, quota-aware, and validation-gated.

Official rule:

- Structural fan-out is not conditional branching.
- Dependency fan-in is not aggregation policy.
- Raw cyclic edges are not loops.
- Loop support must be represented through an explicit LoopNode or equivalent bounded control node.
- Conditional branch support must be represented through an explicit ConditionalBranchNode or equivalent bounded control node.
- Runtime graph mutation must remain outside this family unless separately approved.

## 4. Relationship to Active Control-Flow Contract

This document depends on:

- `docs/specs/execution/circuit_graph_control_flow_contract.md`
- `docs/specs/architecture/execution_model.md`
- `docs/specs/contracts/validation_engine_contract.md`
- `docs/specs/policies/validation_rule_catalog.md`

The active rule is:

- DAG base graph now
- explicit branch/loop node family later

## 5. Why Deferred

Conditional branch and loop support materially increases:

- scheduler complexity
- determinism pressure
- replay complexity
- trace readability burden
- artifact lineage complexity
- quota and timeout accounting complexity
- approval/debugging complexity
- beginner/productization surface complexity

Therefore this family belongs to controlled later expansion, not the current first-success productization line.

## 6. Future Contract Family Members

The branch/loop family should eventually include at least the following documents or sections:

1. Conditional Branch Node Contract
2. Loop Node Contract
3. Branch Decision Record Contract
4. Loop Iteration Record Contract
5. Branch/Loop Validation Rule Addendum
6. Branch/Loop Trace and Artifact Addendum
7. Branch/Loop UI Projection Addendum
8. Branch/Loop Quota and Safety Addendum
9. Branch/Loop Replay Verification Addendum

## 7. Conditional Branch Minimum Requirements

Future branch support must define:

- branch node identity
- decision input binding
- predicate or decision-source model
- branch list
- default branch rule
- multi-match resolution rule
- no-match handling rule
- skipped-path representation
- branch decision record
- replay decision determinism
- validation rule ids
- trace representation
- artifact linkage

A future ConditionalBranchNode must not silently rewrite graph structure.
It may select a path according to declared rules, but the declared possible paths must be visible before execution.

## 8. Loop Minimum Requirements

Future loop support must define:

- loop node identity
- loop body boundary
- loop body reference model
- maximum iteration policy
- stop condition policy
- state carry policy
- per-iteration input mapping
- per-iteration output binding
- per-iteration trace identity
- per-iteration artifact identity
- timeout and quota policy
- cancellation policy
- failure and partial-result policy
- replay verification rule

A future LoopNode must not be implemented as an ordinary raw graph cycle.

## 9. Trace Requirements

Future branch/loop support must preserve trace evidence.

Minimum trace additions:

- branch decision started
- branch decision completed
- branch selected
- branch skipped
- loop started
- loop iteration started
- loop iteration completed
- loop stop condition evaluated
- loop completed
- loop failed
- loop cancelled

Every such event must be tied to run identity, node identity, and deterministic sequence identity.

## 10. Artifact Requirements

Future branch/loop support must preserve append-only artifact behavior.

Rules:

- branch decision artifacts are evidence, not hidden mutation
- loop iteration artifacts must be iteration-scoped
- final loop output must be distinguishable from per-iteration output
- partial loop output must be distinguishable from final output
- skipped branch artifacts must not be fabricated

## 11. Replay Requirements

Future branch/loop execution must be replayable.

Minimum replay constraints:

1. Branch decisions must be reproducible from recorded inputs and policy, or explicitly recorded as non-deterministic decision evidence.
2. Loop iteration count must be recoverable from trace.
3. Stop condition outcomes must be recorded.
4. Per-iteration context changes must be reconstructable or explicitly marked non-replayable.
5. Quota/timeouts/cancellation must be represented in replay evidence.

## 12. Safety and Quota Requirements

Branch/loop support must integrate with safety and quota governance.

Minimum requirements:

- max_iterations required for loops
- max_total_runtime or timeout policy required for loops
- per-iteration quota accounting required where relevant
- branch fan-out must not multiply delivery or side effects without explicit policy
- loop body must not perform unbounded external writes
- safety findings inside loop iterations must be traceable by iteration

## 13. UI Projection Requirements

UI must not hide control-flow complexity.

Minimum UI projection rules:

- branches must show selected and skipped paths
- loops must show iteration count and stop reason
- partial loop output must be labeled as partial
- retry and replay must distinguish branch/loop identity from ordinary node identity
- beginner shell must not expose raw branch/loop internals before appropriate unlock

## 14. Non-Goals

This family does not authorize:

- unrestricted dynamic graph mutation
- runtime scheduler self-modification
- autonomous graph rewrite
- unbounded recursion
- hidden side-effect loops
- cross-run memory loops
- conversational execution loops
- distributed graph execution

Those require separate contracts.

## 15. Promotion Criteria

This family may be promoted from deferred to active only when all of the following are true:

1. first-success product loop is stable
2. execution streaming and trace projection are stable
3. usage quota and safety gates are active
4. validator can reject unsupported branch/loop shapes
5. replay verification can preserve branch/loop evidence
6. UI can distinguish structural fan-out from conditional selection
7. implementation tests cover failure, cancellation, timeout, and replay cases

## 16. Final Decision

Branch and loop support should be preserved as a future capability, but never smuggled into Nexa through ordinary edges.

The base circuit graph remains DAG-first.
Future branch and loop execution must be explicit control-node execution, not accidental cyclic graph semantics.
