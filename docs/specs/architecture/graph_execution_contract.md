# graph_execution_contract.md

Version: 1.0.0

Defines execution semantics of Circuit graphs.

## Core Concepts

Node
Execution unit in the circuit.

Edge
Dependency between nodes.

Channel
Key used to propagate state between nodes.

## Execution Semantics

1. Graph must be topologically sortable.
2. Execution order is determined by dependencies.
3. Node outputs propagate through channels.
4. Artifacts accumulate append-only.

## Failure Rules

Cycle detection MUST fail-fast.

If a cycle exists in the graph:

GraphCycleError MUST be raised.