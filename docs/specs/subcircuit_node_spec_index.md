# Subcircuit Node Spec Index v0.1

## Recommended save path
`docs/specs/subcircuit_node_spec_index.md`

## 1. Purpose

This document is the official index for the SubcircuitNode specification bundle in Nexa.

Its purpose is to:

- define the canonical document set for SubcircuitNode
- explain the role of each document
- fix the recommended reading order
- clarify which document is authoritative for which question
- reduce future ambiguity during implementation and review

This index does not replace the detailed specs.
It organizes them.

## 2. Why This Index Exists

SubcircuitNode is not a one-file feature.

It affects multiple specification layers at once:

- architecture
- node contract
- savefile representation
- official example usage

Without an index, future implementation work may drift because different documents answer different kinds of questions.

This index exists to prevent that drift.

## 3. Canonical SubcircuitNode Spec Bundle

The canonical v0.1 bundle consists of four documents.

### 3.1 Architecture
Path:

    docs/specs/architecture/subcircuit_node_architecture.md

Role:
- defines what SubcircuitNode is
- fixes its architectural position in Nexa
- protects core runtime invariants
- prevents SubcircuitNode from being misread as a new top-level execution unit

### 3.2 Contract
Path:

    docs/specs/contracts/subcircuit_node_contract.md

Role:
- defines canonical fields and rules
- defines parent-child boundary rules
- defines validation expectations
- defines runtime, trace, artifact, and failure contract expectations

### 3.3 Savefile Extension
Path:

    docs/specs/storage/savefile_subcircuit_extension.md

Role:
- defines how SubcircuitNode is represented in `.nex`
- defines `kind: "subcircuit"` storage semantics
- defines `internal:` child reference direction
- defines local `subcircuits` registry direction

### 3.4 Official Example
Path:

    docs/specs/examples/review_bundle_subcircuit_example.md

Role:
- provides the first official practical example
- demonstrates parent-child boundary usage
- demonstrates explicit mapping and binding
- provides the first reusable validation example

## 4. Recommended Reading Order

The official reading order is:

1. `subcircuit_node_architecture.md`
2. `subcircuit_node_contract.md`
3. `savefile_subcircuit_extension.md`
4. `review_bundle_subcircuit_example.md`

Reason:

- architecture first fixes identity
- contract then fixes rules
- savefile then fixes representation
- example then fixes applied interpretation

This order should be followed when reviewing, implementing, or validating SubcircuitNode.

## 5. Which Document Answers Which Question

### 5.1 “What is SubcircuitNode?”
Use:

    subcircuit_node_architecture.md

### 5.2 “What exact fields and rules does it have?”
Use:

    subcircuit_node_contract.md

### 5.3 “How is it stored in `.nex`?”
Use:

    savefile_subcircuit_extension.md

### 5.4 “What does the first official real example look like?”
Use:

    review_bundle_subcircuit_example.md

### 5.5 “Which document wins if there is confusion?”
Use the following priority:

1. Architecture
2. Contract
3. Savefile Extension
4. Example

Interpretation rule:
- the example must not override the contract
- the contract must not violate the architecture
- the savefile extension must implement the contract
- the example must conform to all of the above

## 6. Core Cross-Document Invariants

All documents in this bundle must preserve the same core invariants.

### 6.1 Node remains the sole runtime execution unit
SubcircuitNode must not turn Circuit into a parallel execution unit.

### 6.2 Parent-child exchange is mapping-based
Parent-child data exchange is allowed only through explicit `input_mapping` and `output_binding`.

### 6.3 Parent-child runtime boundaries remain explicit
Parent and child must not silently collapse into one undifferentiated runtime truth.

### 6.4 Child circuits are referenced, not flattened
Child internals must not be treated as parent-local nodes in savefile or runtime truth.

### 6.5 Trace and artifact provenance remain intact
Child-owned trace and artifact identity must remain visible and linked, not silently absorbed.

## 7. First Official Validation Example Binding

The official first validation example for the SubcircuitNode bundle is:

    Review Bundle

This example is normative as an example, but not above the contract.

Meaning:
- it is the first official reference implementation pattern
- it is the first recommended validator fixture direction
- it does not overrule the architecture or contract layers

## 8. Recommended Review Workflow

When reviewing future SubcircuitNode changes, use this order:

1. Check architecture compatibility
2. Check contract compatibility
3. Check savefile compatibility
4. Check example consistency

This avoids the common mistake of approving a convenient example that violates the deeper architectural rules.

## 9. Recommended Implementation Workflow

When implementing SubcircuitNode in code, use this order:

1. add schema / model vocabulary
2. add validator rules
3. add savefile handling
4. add runtime execution boundary
5. add trace / artifact linkage
6. validate against Review Bundle example

This implementation order follows the same logic as the document stack.

## 10. Non-Goals of This Index

This index does not:
- define new SubcircuitNode behavior
- add new savefile fields
- introduce new runtime policy
- replace detailed validator rules
- replace the official example

It is an organizing document only.

## 11. Final Rule

The SubcircuitNode specification bundle must be read and implemented as one connected package, not as isolated documents.

Final statement:

`subcircuit_node_spec_index.md` is the official index for the SubcircuitNode v0.1 specification bundle and defines the canonical document set, authority order, and review sequence for the feature.
