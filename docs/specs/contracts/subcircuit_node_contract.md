# Subcircuit Node Contract v0.1

## Recommended save path
`docs/specs/contracts/subcircuit_node_contract.md`

## 1. Purpose

This document defines the canonical contract for `SubcircuitNode` in Nexa.

Its purpose is to make SubcircuitNode:

- schema-stable
- validator-checkable
- runtime-executable
- traceable
- safe under Nexa core invariants

This contract sits below the architecture document and above implementation details.

Architecture tells us what SubcircuitNode is.
This contract tells us exactly what fields, rules, and boundaries it must obey.

## 2. Contract Position

SubcircuitNode is a node-kind.

It is not:

- a new top-level execution unit
- a free-form embedded runtime
- a direct replacement for Node

It is:

- a node wrapper
- a bounded child-circuit execution boundary
- a mapping-based parent-child composition mechanism

## 3. Canonical Identity

A SubcircuitNode must satisfy all of the following:

1. It appears inside `circuit.nodes[]`.
2. It declares `kind: "subcircuit"`.
3. It contains an `execution.subcircuit` block.
4. It resolves a child circuit through `child_circuit_ref`.
5. It exchanges data only through `input_mapping` and `output_binding`.
6. It returns node-level outputs to the parent circuit.
7. It preserves parent-child runtime separation.

## 4. Canonical Shape

Minimum canonical shape:

    node_id: string
    kind: "subcircuit"
    label: optional string
    execution:
      subcircuit:
        child_circuit_ref: string
        input_mapping: object
        output_binding: object
        runtime_policy: optional object

No other shape may be treated as canonical SubcircuitNode.

## 5. Required Fields

### 5.1 `node_id`
Stable identifier for the parent-level node.

Rules:
- required
- must be unique within the parent circuit
- must follow general node id rules

### 5.2 `kind`
Must be exactly:

    "subcircuit"

Rules:
- required
- any other value is invalid for this contract

### 5.3 `execution.subcircuit`
The canonical subcircuit execution block.

Rules:
- required when `kind == "subcircuit"`
- forbidden when `kind != "subcircuit"`

### 5.4 `child_circuit_ref`
Reference to the child circuit definition.

Rules:
- required
- must resolve successfully
- v0.1 canonical form is reference-based
- `internal:<name>` is the preferred v0.1 local form

Examples:
- `internal:review_bundle`
- `registry:review_bundle_v1` is future-compatible but optional for v0.1

### 5.5 `input_mapping`
Explicit map from parent-visible values to child inputs.

Rules:
- required
- must be an object
- keys represent child input names
- values represent parent-readable paths
- wildcard and implicit full-context pass-through are forbidden

Example shape:

    question -> input.question
    draft -> node.draft_generator.output.result

### 5.6 `output_binding`
Explicit map from child outputs to parent node outputs.

Rules:
- required
- must be an object
- keys represent parent node-level output fields
- values must reference child outputs
- wildcard export is forbidden
- implicit full-child export is forbidden

Example shape:

    result -> child.output.result
    confidence -> child.output.confidence

### 5.7 `runtime_policy`
Optional execution modifiers for the child boundary.

Allowed v0.1 examples:
- `fail_fast`
- `max_child_depth`
- `trace_mode`

Rules:
- optional
- unknown policy keys may be ignored only in permissive modes
- strict modes may reject unsupported keys

## 6. Parent-Child Boundary Rules

### 6.1 Allowed parent -> child flow
Allowed only through explicit `input_mapping`.

### 6.2 Allowed child -> parent flow
Allowed only through explicit `output_binding`.

### 6.3 Forbidden direct access
Forbidden:
- child direct mutation of parent working context
- parent direct read of child internal runtime namespace
- automatic export of all child outputs
- flattening child internals into parent-local runtime state

## 7. Parent Input Path Rules

Values in `input_mapping` must be valid parent-readable paths.

Minimum v0.1 allowed forms:
- `input.<field>`
- `node.<node_id>.output.<field>`

Future namespaces may exist later, but v0.1 must not pretend they exist unless implemented.

Invalid examples:
- empty string
- raw object payload instead of a path
- raw list payload instead of a path
- non-existent parent node reference
- wildcard path
- hidden direct child-internal path

## 8. Child Output Path Rules

Values in `output_binding` must be valid child output references.

Minimum canonical form:

    child.output.<field>

Rules:
- referenced child output field must actually exist
- binding to undeclared child output is invalid
- direct write to parent engine-owned namespaces is forbidden

## 9. Child Circuit Resolution Rules

### 9.1 Resolution requirement
`child_circuit_ref` must resolve before execution.

### 9.2 v0.1 internal resolution
If the ref begins with `internal:`, resolution must look up the child in the local subcircuit registry.

Example:
- `internal:review_bundle`
- resolves to local `subcircuits.review_bundle`

### 9.3 Missing child circuit
If resolution fails, the SubcircuitNode is invalid.

## 10. Child Circuit Minimum Requirements

A resolved child circuit must itself satisfy minimum circuit validity.

Minimum required:
- at least one node
- valid internal node ids
- valid internal edges
- valid entry handling according to current engine rules
- declared outputs
- structurally valid internal references

If the child circuit is invalid, the parent SubcircuitNode must be invalid.

## 11. Recursion and Depth Rules

### 11.1 Direct self-reference is forbidden
A subcircuit may not directly reference itself.

### 11.2 Cycle reference is forbidden
Multi-step cyclic subcircuit reference is forbidden.

Examples of forbidden patterns:
- A -> A
- A -> B -> A
- A -> B -> C -> A

### 11.3 Depth must be bounded
A maximum child depth must exist.

Preferred v0.1 default:
- maximum depth: 2

If exceeded, validation must fail unless an explicit approved override exists.

## 12. Validation Findings and Error Codes

Minimum canonical error codes:

- `SUBCIRCUIT_KIND_MISMATCH`
- `SUBCIRCUIT_NODE_MISSING_BLOCK`
- `SUBCIRCUIT_CHILD_REF_MISSING`
- `SUBCIRCUIT_CHILD_REF_NOT_FOUND`
- `SUBCIRCUIT_INVALID_INPUT_MAPPING`
- `SUBCIRCUIT_INVALID_OUTPUT_BINDING`
- `SUBCIRCUIT_CHILD_OUTPUT_NOT_FOUND`
- `SUBCIRCUIT_PARENT_PATH_INVALID`
- `SUBCIRCUIT_RECURSIVE_REFERENCE`
- `SUBCIRCUIT_MAX_DEPTH_EXCEEDED`
- `SUBCIRCUIT_CHILD_CIRCUIT_INVALID`

These codes should be preserved as explicit machine-readable reasons.

## 13. Runtime Contract

When executed, a SubcircuitNode must behave like a parent-level node.

Runtime sequence:

1. Parent runtime reaches the SubcircuitNode.
2. Parent resolves `input_mapping`.
3. Child input payload is built.
4. Child runtime boundary is created.
5. Child circuit executes.
6. Child outputs are collected.
7. Parent resolves `output_binding`.
8. Parent records node-level output.
9. Parent records trace linkage.

Parent scheduler must not schedule child nodes as if they were parent-local nodes.

## 14. Output Contract

A SubcircuitNode must reduce child execution into node-level parent-visible outputs.

Parent-visible output is allowed to include:
- result fields
- confidence-like fields
- summaries
- references to child trace
- references to child artifacts

Parent-visible output must not expose arbitrary child internals as raw engine truth.

## 15. Trace Contract

SubcircuitNode must preserve trace linkage.

Parent trace must at minimum be able to record:
- subcircuit node started
- child run started
- child run finished
- subcircuit node finished
- child run id
- child trace ref
- final status

Child trace remains child-owned execution history.

Parent trace must not flatten the full child trace into one undifferentiated event stream.

## 16. Artifact Contract

Child artifacts remain child-owned.

Parent may receive:
- artifact refs
- artifact summaries
- artifact count / type summary

Parent must not silently absorb child artifact bodies as if they were parent-created originals.

Append-only meaning must be preserved.

## 17. Failure Contract

Minimum v0.1 expected behavior:

- child failure must be visible at parent node level
- parent must receive a failure summary
- failure linkage to child trace must exist
- `fail_fast` is the preferred base policy

Later policies may expand, but v0.1 must not hide child failure.

## 18. Review Bundle Official Example

The first official example bound to this contract is `Review Bundle`.

Recommended parent shape:

    Input
    -> Draft Generator
    -> Review Bundle (SubcircuitNode)
    -> Final Output

Recommended child shape:

    Draft Critic
    Evidence Check
    Review Synthesizer

Preferred role alignment:
- GPT for generation / synthesis
- Claude for critique
- Perplexity for evidence check

## 19. Non-Goals for v0.1

This contract does not include:
- dynamic runtime mutation of child circuit shape
- unrestricted recursive orchestration
- automatic child output explosion
- direct shared parent-child context
- child internals becoming parent scheduler units
- silent Designer-originated bypass of approval flow

## 20. Final Rule

SubcircuitNode is valid only when all of the following are true:

- it is declared as a node-kind
- its child circuit resolves
- its mappings are explicit
- its recursion is bounded
- its child outputs are declared
- its parent-child boundary is preserved
- its runtime behavior remains node-based

Final statement:

SubcircuitNode is a bounded, mapping-based node wrapper for child-circuit execution.
It expands composition power without changing Nexa's rule that Node remains the sole runtime execution unit.
