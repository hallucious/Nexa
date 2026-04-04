# Subcircuit Node Implementation Batches v0.2

## Recommended save path
`docs/specs/implementation/subcircuit_node_implementation_batches.md`

## 1. Purpose

This document defines the implementation batching plan for SubcircuitNode in Nexa.

Its purpose is to convert the existing SubcircuitNode specification bundle into a practical coding sequence that is:

- implementable
- reviewable
- bounded
- less regression-prone
- aligned with Nexa core invariants

This document does not add new SubcircuitNode behavior.
It organizes implementation work.

## 2. Why This Document Exists

## 2.1 Current Status

Current judgment for the v0.2 implementation line:

- Batch 1 is considered closed at closure-quality level
- Batch 1 support is regression-backed across parser, validator, runtime, node execution, review-bundle example, load path, and write path
- Batch 2 core observability / inspectability is now implemented at a practical level
- Review Bundle example lock is already real and regression-backed in the repository
- remaining Subcircuit work is optional deepening or later infrastructure quality work unless a concrete regression is discovered


The SubcircuitNode specification bundle already defines:

- architectural position
- contract rules
- savefile representation
- official example
- document authority order

However, those documents do not by themselves fix the implementation batching strategy.

Because SubcircuitNode affects multiple engine layers at once, implementation order matters.

It touches:

- parser / loader
- validator
- typed model / savefile handling
- runtime execution boundary
- context boundary rules
- trace linkage
- artifact linkage
- official example validation

Without a batching document, implementation may drift into:
- oversized first changes
- parser-only partial support
- runtime support without validator safety
- inconsistent example handling
- blurred P1/P2 boundaries

This document exists to prevent that drift.

## 3. Core Implementation Principle

SubcircuitNode must be implemented in a way that preserves all of the following:

- Node remains the sole runtime execution unit
- execution remains dependency-based
- parent-child exchange remains mapping-based
- parent-child direct context sharing remains forbidden
- child circuits remain wrapper-mediated, not promoted to top-level runtime peers

Implementation batching must protect these invariants first.

## 4. Canonical Batch Structure

The official implementation plan has two batches.

### Batch 1
Subcircuit Core Enablement

### Batch 2
Subcircuit Completion and Review Bundle Lock

This is the canonical batching direction for v0.1.

## 5. Batch 1 — Subcircuit Core Enablement

### 5.1 Goal

Batch 1 exists to reach this minimum state:

SubcircuitNode can be parsed, validated, and executed as a bounded node-level wrapper.

This is the smallest implementation state that still counts as real support.

### 5.2 Included Work

Batch 1 includes the following four implementation steps:

1. Contract and schema foundation
2. Structural validation core
3. Runtime execution core
4. Context boundary and output discipline

### 5.3 Detailed Scope

#### 5.3.1 Contract and schema foundation
Implementation must add the minimum shared vocabulary required for SubcircuitNode.

Included:
- `kind = "subcircuit"`
- `execution.subcircuit`
- `child_circuit_ref`
- `input_mapping`
- `output_binding`
- optional `runtime_policy`
- `internal:` local child reference direction
- local `subcircuits` registry support

Expected outputs:
- schema/model vocabulary exists
- savefile reader can recognize subcircuit nodes
- local child references can be resolved syntactically

#### 5.3.2 Structural validation core
Implementation must reject structurally unsafe subcircuit definitions before runtime.

Included:
- kind/schema mismatch detection
- missing child reference detection
- invalid `input_mapping` detection
- invalid `output_binding` detection
- missing child output detection
- child structural invalidity propagation
- self-reference rejection
- cycle rejection
- max depth enforcement

Expected outputs:
- validator findings are explicit
- invalid structures fail early
- child invalidity cannot hide inside a parent wrapper

#### 5.3.3 Runtime execution core
Implementation must add a true SubcircuitNode execution path.

Included:
- SubcircuitNode executor
- parent input mapping resolution
- child runtime boundary creation
- child circuit execution
- child output collection
- parent output binding
- parent-visible node-level output return

Expected outputs:
- parent runtime can execute a subcircuit node as one node
- child internals do not become parent-local scheduler truth
- parent receives bound node-level outputs only

#### 5.3.4 Context boundary and output discipline
Implementation must enforce explicit parent-child boundaries.

Included:
- no child direct mutation of parent working context
- no parent direct read of child internal runtime namespace
- no implicit child output explosion
- wrapper-level output discipline

Expected outputs:
- all parent-child exchange remains mapping-based
- runtime contract violations fail explicitly
- wrapper output remains node-shaped

### 5.4 Batch 1 Completion Criteria

Batch 1 is complete only if all of the following are true:

1. savefile parsing recognizes `kind: "subcircuit"`
2. `internal:` child references resolve through local `subcircuits`
3. invalid subcircuit structure is rejected by validator
4. child invalidity propagates to the parent wrapper
5. parent runtime can execute a subcircuit node
6. child output binding creates parent node-level outputs
7. parent-child direct context collapse is prevented

### 5.5 Batch 1 Non-Goals

Batch 1 intentionally does not require:
- rich trace summaries
- artifact summary presentation
- expanded failure policy families
- polished fan-in / fan-out inspectability
- official example end-to-end lock as a completed usability package

Those belong to Batch 2.

## 6. Batch 2 — Subcircuit Completion and Review Bundle Lock

### 6.1 Goal

Batch 2 exists to move SubcircuitNode from minimal support to usable, inspectable, and officially validated support.

Implementation reality update:
- core Batch 2 observability / inspectability work is implemented in practice
- the remaining value in this batch is interpretive/documentary closure and any later optional deepening, not reopening Batch 1-like enablement work

### 6.2 Included Work

Batch 2 includes the following four implementation steps conceptually:

5. Trace and observability completion
6. Artifact and failure completion
7. Fan-in / fan-out inspectability
8. Review Bundle end-to-end example lock

Implementation reality note:
- steps 5-7 are materially implemented at core level
- step 8 is already regression-backed in the repository and should no longer be treated as an open future-only dependency

### 6.3 Detailed Scope

#### 6.3.1 Trace and observability completion
Implementation must make SubcircuitNode debuggable.

Included:
- parent trace summary events
- child run id linkage
- child trace reference linkage
- child status summary
- child duration summary
- warning/error count summary

Expected outputs:
- parent trace clearly shows child execution boundary
- child history remains linked, not flattened
- subcircuit runs are inspectable

#### 6.3.2 Artifact and failure completion
Implementation must make child artifacts and failures visible without breaking provenance.

Included:
- child artifact ownership preservation
- parent-facing artifact refs / summaries
- child failure summary propagation
- preferred base policy: `fail_fast`

Expected outputs:
- child artifacts remain child-owned
- parent sees references and summaries only
- child failures remain visible at wrapper level

#### 6.3.3 Fan-in / fan-out inspectability
Implementation must support the official example shape without hiding provenance.

Included:
- inspectable child multi-input structure
- inspectable child output provenance
- practical support for review-bundle-like internal shapes

Expected outputs:
- internal review bundle style child circuits are understandable in runtime inspection
- child output origins are not opaque blobs

#### 6.3.4 Review Bundle end-to-end example lock
Implementation must validate the first official example as a real support target.

Included:
- parent example support
- local `subcircuits` registry support
- GPT / Claude / Perplexity role mapping compatibility at example level
- validator fixture direction
- runtime fixture direction

Expected outputs:
- Review Bundle becomes the first official implementation validation pattern
- parser / validator / runtime all agree on the example

### 6.4 Batch 2 Completion Criteria

Batch 2 is considered core-complete at the current baseline if all of the following are true:

1. parent trace shows subcircuit execution boundary and linkage
2. child artifact provenance remains intact
3. child failure visibility is preserved
4. official review-bundle-shaped child circuit is inspectable
5. Review Bundle passes parser / validator / runtime validation flow

Current repository judgment:
- the core criteria above are satisfied at a practical level
- future work should be framed as deeper quality extensions, not as “Batch 2 has not started”

### 6.5 Batch 2 Non-Goals

Batch 2 still does not include:
- unrestricted recursive orchestration
- dynamic child mutation during runtime
- cross-savefile distributed subcircuit package registry
- child circuits becoming independent top-level runtime roots
- unrestricted Designer-originated automatic insertion without approval flow

## 7. Why the Implementation Is Split This Way

This batching is intentional.

### 7.1 Why Batch 1 is not smaller
If schema is added without validator and executor support, the system gains dead or unsafe partial support.

### 7.2 Why Batch 2 is not merged into Batch 1
Trace, artifact, and official example lock matter, but they do not define minimum real support.
Keeping them in Batch 2 reduces first-batch regression pressure while still preserving the planned completion path.

### 7.3 Why this is still one connected feature
Even though there are two batches, they are one connected SubcircuitNode feature line.
Batch 2 is not optional design drift.
It is the official completion layer.

## 8. Recommended Review Order During Implementation

For each implementation change, use this review order:

1. architecture compatibility
2. contract compatibility
3. savefile compatibility
4. batch scope correctness
5. example consistency

This keeps implementation aligned with the SubcircuitNode spec bundle.

## 9. Recommended Testing Order

Recommended testing sequence:

1. parser recognition tests
2. child ref resolution tests
3. validator negative tests
4. recursion / cycle safety tests
5. runtime wrapper execution tests
6. boundary enforcement tests
7. trace linkage tests
8. artifact / failure visibility tests
9. Review Bundle end-to-end example tests

This order matches the implementation batches.

## 10. Relationship to the Official Spec Bundle

This implementation batching document depends on the following documents:

- `docs/specs/architecture/subcircuit_node_architecture.md`
- `docs/specs/contracts/subcircuit_node_contract.md`
- `docs/specs/storage/savefile_subcircuit_extension.md`
- `docs/specs/examples/review_bundle_subcircuit_example.md`
- `docs/specs/subcircuit_node_spec_index.md`

Authority rule:
- this document organizes implementation work
- it does not override higher-level architectural or contract rules

## 11. Final Rule

SubcircuitNode implementation must not be treated as a single parser change or a single runtime shortcut.

Final statement:

`subcircuit_node_implementation_batches.md` is the official batching document for implementing SubcircuitNode in Nexa and defines the canonical two-batch path from core enablement to completed official example support.
