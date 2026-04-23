# Subcircuit Node Architecture v0.1

## Recommended save path
`docs/specs/architecture/subcircuit_node_architecture.md`

## 1. Purpose

This document defines the official architectural position of `SubcircuitNode` in Nexa.

Its purpose is to enable hierarchical circuit composition without violating Nexa's core runtime invariants.

SubcircuitNode allows a parent circuit to include a child circuit as a reusable architectural unit while preserving the rule that runtime execution still happens through Nodes.

## 2. Core Decision

A child circuit must not become a new top-level runtime execution unit.

Official rule:

- Circuit remains a connection structure.
- Node remains the sole runtime execution unit.
- A child circuit may only appear inside a parent circuit through a `SubcircuitNode` wrapper.
- The wrapper is a node-kind that executes a child circuit through a bounded runtime boundary.

In short:

**SubcircuitNode is a node-kind wrapper that executes a child circuit while preserving Node as the sole runtime execution unit.**

## 3. Architectural Position

Official high-level structure:

```text
Circuit
↓
Node
↓
Execution Runtime
↓
Prompt / Provider / Plugin
↓
Artifact
↓
Trace
```

Hierarchical extension with SubcircuitNode:

```text
Parent Circuit
└─ SubcircuitNode
   └─ Child Circuit
      ├─ Node A
      ├─ Node B
      └─ Node C
```

Interpretation:

- Parent circuit sees only `SubcircuitNode` as a node.
- Parent scheduler does not directly schedule child nodes.
- Child circuit is executed through a child runtime boundary.
- Parent receives only node-level outputs from the wrapper.

## 4. Relationship to Core Nexa Invariants

SubcircuitNode must preserve all of the following.

### 4.1 Node remains the sole execution unit
SubcircuitNode does not promote Circuit into a direct execution unit.
The runtime boundary remains node-based.

### 4.2 Execution remains dependency-based
Subcircuit support must not collapse Nexa into a fixed procedural pipeline.
Parent and child circuits must still obey dependency-based execution.

### 4.3 Working Context remains central
Resources inside a node still communicate through Working Context.
SubcircuitNode does not introduce ad hoc direct wiring between runtime internals.

### 4.4 Plugin remains a tool, not a stage
Subcircuit support must not reinterpret plugin semantics.
Prompt / provider / plugin remain the user-composed execution resources.

### 4.5 Artifact append-only and trace first-class must remain intact
Child execution may produce artifacts and traces, but those must preserve provenance and append-only meaning.

## 5. Boundary Model

SubcircuitNode introduces a **parent-child runtime boundary**.

This boundary exists to prevent child circuit internals from collapsing into parent runtime truth.

### 5.1 Parent → child exchange
Allowed only through explicit `input_mapping`.

### 5.2 Child → parent exchange
Allowed only through explicit `output_binding`.

### 5.3 Disallowed
The following are forbidden:

- child direct mutation of parent working context
- parent direct read of child internal runtime namespace
- automatic child output explosion into parent truth
- flattening child nodes into the parent scheduler as if they were local nodes

## 6. Data Exchange Rule

The parent-child contract is mapping-based, not shared-state-based.

Official statement:

**Parent-child data exchange is allowed only through explicit `input_mapping` and `output_binding`.**

Meaning:

- parent prepares a child input payload
- child runs within its own runtime boundary
- child returns explicit outputs
- parent binds those outputs into node-level parent outputs

## 7. Runtime Semantics

SubcircuitNode execution follows this model:

```text
1. Parent runtime reaches SubcircuitNode
2. Parent resolves input_mapping
3. Child input payload is created
4. Child runtime is created
5. Child circuit executes
6. Child outputs are collected
7. Parent applies output_binding
8. Parent records SubcircuitNode result as node-level output
```

The parent runtime must not expose child internals as if they were parent-local node execution state.

## 8. Savefile Semantics

SubcircuitNode is represented as a node inside `circuit.nodes[]`.
It is not represented as a new top-level execution artifact.

Canonical direction:

- `kind: "subcircuit"`
- `execution.subcircuit.child_circuit_ref`
- `execution.subcircuit.input_mapping`
- `execution.subcircuit.output_binding`
- optional `execution.subcircuit.runtime_policy`

The child circuit may be referenced through:

- internal savefile registry reference
- future registry/library reference

## 9. Trace Semantics

Parent and child trace must remain separate but linked.

### Parent trace must record at least:
- subcircuit node started
- child run started
- child run finished
- subcircuit node finished
- child run reference
- child trace reference

### Child trace:
- remains child-owned execution history
- must not be flattened into parent event stream as if it were the same level of execution history

## 10. Artifact Semantics

Child artifacts remain child-owned.
Parent may receive references and summaries, but should not absorb child artifacts as if they were parent-native originals.

Official direction:

- child artifact ownership remains with child execution
- parent receives artifact references / summaries
- append-only meaning is preserved

## 11. Validation Responsibilities

SubcircuitNode requires dedicated validation beyond generic node validation.

Minimum required checks:

- kind/schema match
- child_circuit_ref existence
- valid `input_mapping`
- valid `output_binding`
- child output existence
- self-reference prohibition
- cycle prohibition
- max depth enforcement
- child invalidity propagation to parent

## 12. First Official Validation Example

The first official SubcircuitNode validation example is:

**Review Bundle**

Parent structure:

```text
Input
→ Draft Generator
→ Review Bundle (SubcircuitNode)
→ Final Output
```

Child structure:

```text
Draft Critic
Evidence Check
Review Synthesizer
```

Role alignment:

- GPT: draft generation / synthesis
- Claude: critique
- Perplexity: evidence check

This is the preferred v0.1 example because it validates:

- parent-child boundary
- input/output mapping
- trace separation
- reusable subcircuit semantics

## 13. Non-Goals for v0.1

The following are explicitly out of scope for the first SubcircuitNode architecture cut:

- dynamic child circuit mutation during runtime
- unrestricted recursive orchestration
- direct shared parent-child context
- automatic child node exposure in parent graph view as execution truth
- circuit becoming a parallel execution unit beside node
- silent Designer-originated structural insertion bypassing normal approval flow

## 14. Final Decision

SubcircuitNode is a core architectural extension for Nexa, not a cosmetic convenience feature.

However, it must be implemented in a way that preserves Nexa's identity:

- Circuit is structure.
- Node is execution.
- Runtime boundaries remain explicit.
- Parent-child exchange remains mapping-based.
- Trace and artifact provenance remain intact.

Final statement:

**SubcircuitNode enables hierarchical circuit composition in Nexa without violating the rule that Node remains the sole runtime execution unit.**
