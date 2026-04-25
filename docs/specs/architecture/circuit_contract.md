Spec ID: circuit_contract
Version: 1.1.0
Status: Partial
Category: architecture
Depends On:

# Circuit Contract (Node Circuit Definition Language)

Purpose:
Defines the canonical JSON schema for Node-based AI collaboration circuits.

Core Concepts:
- Node (ai_task | subgraph)
- Edge (next | conditional | on_fail)
- Exit Policy
- Deterministic Canonicalization
- Strict Validation

This document formalizes the circuit definition language as the single source of truth for **orchestration definition**.
Execution/orchestration enforcement is performed by the Engine/Runtime layer.

See BLUEPRINT.md for architectural context.

---

## Control-Flow Clarification Addendum v1.2.0

Detailed circuit graph control-flow semantics are defined in:

`docs/specs/execution/circuit_graph_control_flow_contract.md`

Interpretation rules:

1. Circuit graphs are not limited to linear pipelines.
2. Structural fan-out is allowed.
3. Dependency fan-in is allowed.
4. Raw graph cycles are invalid and must be rejected by validation.
5. Multiple outgoing edges do not by themselves mean conditional branching.
6. Multiple incoming edges do not by themselves define aggregation semantics.
7. Explicit ConditionalBranchNode and LoopNode support remains deferred under the engine contract family.
8. Runtime graph mutation remains prohibited unless a future dynamic graph mutation contract is explicitly promoted.

This addendum exists to prevent the older edge terminology in this document from being misread as permission for arbitrary cyclic, dynamic, or hidden control-flow behavior.
