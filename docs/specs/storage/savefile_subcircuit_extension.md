# Savefile Subcircuit Extension v0.1

## Recommended save path
`docs/specs/storage/savefile_subcircuit_extension.md`

## 1. Purpose

This document defines how `SubcircuitNode` is represented inside Nexa savefiles.

Its purpose is to extend the current `.nex` savefile family so that hierarchical circuit composition becomes possible without changing Nexa's core identity.

This document is storage-focused.
It does not redefine runtime identity.
Node remains the sole runtime execution unit.

## 2. Core Decision

Subcircuit support must be represented inside the existing node-based savefile structure.

Official rule:

- A subcircuit is not a new top-level execution unit in savefile structure.
- A child circuit appears through a node entry with `kind: "subcircuit"`.
- Child circuit definitions are referenced, not treated as parent-level runtime peers.
- The preferred v0.1 local reference form is `internal:<name>` backed by a local `subcircuits` registry.

In short:

**A subcircuit is represented as `kind: "subcircuit"` inside `circuit.nodes[]`, not as a new top-level execution unit.**

## 3. Savefile Position

Canonical `.nex` direction:

    meta
    circuit
    resources
    state
    runtime?
    ui?
    designer?
    validation?
    approval?
    lineage?

Subcircuit support extends this structure in two places:

1. `circuit.nodes[]`
2. optional top-level `subcircuits`

## 4. Canonical Parent Node Shape

Minimum parent-side node representation:

    node_id: string
    kind: "subcircuit"
    label: optional string
    execution:
      subcircuit:
        child_circuit_ref: string
        input_mapping: object
        output_binding: object
        runtime_policy: optional object

This is the canonical storage form for a SubcircuitNode.

## 5. Canonical Field Semantics

### 5.1 `kind: "subcircuit"`
Marks the node as a SubcircuitNode.

Rules:
- required for subcircuit nodes
- must not be used by non-subcircuit nodes

### 5.2 `execution.subcircuit`
The dedicated subcircuit execution block.

Rules:
- required when `kind == "subcircuit"`
- forbidden for other node kinds unless future schema explicitly changes this

### 5.3 `child_circuit_ref`
Reference to the child circuit definition.

Preferred v0.1 local form:

    internal:review_bundle

Meaning:
- the child circuit is looked up in top-level `subcircuits.review_bundle`

### 5.4 `input_mapping`
Maps parent-readable values into child inputs.

Example:

    question -> input.question
    draft -> node.draft_generator.output.result

### 5.5 `output_binding`
Maps child outputs back into parent node-level outputs.

Example:

    result -> child.output.result
    confidence -> child.output.confidence
    reasoning_summary -> child.output.reasoning_summary

### 5.6 `runtime_policy`
Optional child-boundary modifiers.

Possible v0.1 examples:
- `fail_fast`
- `max_child_depth`
- `trace_mode`

## 6. Optional Top-Level `subcircuits` Registry

### 6.1 Purpose
The `subcircuits` registry stores locally declared child circuit definitions.

It exists so that parent circuits can reference reusable local circuit fragments without turning them into top-level runtime peers.

### 6.2 Canonical role
`subcircuits` is a local registry of child circuit definitions.
It is not a parallel runtime root.

### 6.3 Canonical shape

    subcircuits:
      review_bundle:
        nodes: [...]
        edges: [...]
        entry: ...
        outputs: [...]

### 6.4 Resolution rule
If a parent node uses:

    child_circuit_ref: internal:review_bundle

then the savefile must contain:

    subcircuits.review_bundle

Otherwise validation fails.

## 7. Child Circuit Storage Requirements

A child circuit stored inside `subcircuits` must look like a circuit definition, not an arbitrary blob.

Minimum required child fields:
- `nodes`
- `edges`
- `outputs`

Optional or engine-dependent fields:
- `entry`
- metadata-like future additions

A child circuit must remain structurally valid under the current circuit validation rules.

## 8. Parent-Child Storage Boundary

The savefile must preserve parent-child separation.

Required interpretation:
- parent circuit owns parent nodes and edges
- child circuit owns its own internal nodes and edges
- parent stores only the wrapper node and its mapping contract
- child internals do not become parent-local nodes in stored structure

Forbidden storage interpretation:
- flattening child nodes into parent `circuit.nodes[]`
- mixing child edges directly into parent edge set without a wrapper boundary
- storing child outputs as if they were already parent output truth

## 9. Example Parent Savefile Fragment

Canonical parent fragment:

    circuit:
      nodes:
        - node_id: draft_generator
          kind: provider
          label: Draft Generator
          execution:
            provider:
              provider_id: openai:gpt
              model: gpt-main
              prompt_ref: draft_prompt

        - node_id: review_bundle_stage
          kind: subcircuit
          label: Review Bundle Stage
          execution:
            subcircuit:
              child_circuit_ref: internal:review_bundle
              input_mapping:
                question: input.question
                draft: node.draft_generator.output.result
              output_binding:
                result: child.output.result
                confidence: child.output.confidence
                reasoning_summary: child.output.reasoning_summary
              runtime_policy:
                fail_fast: true
                max_child_depth: 2
                trace_mode: summary

## 10. Example `subcircuits` Fragment

Canonical local child registry fragment:

    subcircuits:
      review_bundle:
        nodes:
          - node_id: draft_critic
            kind: provider
            label: Draft Critic
            execution:
              provider:
                provider_id: anthropic:claude
                model: claude-review
                prompt_ref: critic_prompt

          - node_id: evidence_check
            kind: provider
            label: Evidence Check
            execution:
              provider:
                provider_id: perplexity:search
                model: perplexity-main
                prompt_ref: search_prompt

          - node_id: review_synthesizer
            kind: provider
            label: Review Synthesizer
            execution:
              provider:
                provider_id: openai:gpt
                model: gpt-synth
                prompt_ref: synth_prompt

        edges:
          - from: draft_critic
            to: review_synthesizer
          - from: evidence_check
            to: review_synthesizer

        entry: draft_critic

        outputs:
          - name: result
            source: node.review_synthesizer.output.result
          - name: confidence
            source: node.review_synthesizer.output.confidence
          - name: reasoning_summary
            source: node.review_synthesizer.output.reasoning_summary

## 11. Storage Validation Rules

Minimum savefile validation rules for Subcircuit extension:

1. `kind == "subcircuit"` requires `execution.subcircuit`
2. `execution.subcircuit` requires `child_circuit_ref`
3. `input_mapping` must be present and must be an object
4. `output_binding` must be present and must be an object
5. `internal:<name>` refs require matching `subcircuits.<name>`
6. referenced child outputs must exist
7. child circuit must be structurally valid
8. recursive self-reference must be rejected
9. cycle reference must be rejected
10. depth overflow must be rejected

## 12. Role-Aware Savefile Implications

### 12.1 Working Save
Working Save may contain subcircuit definitions even when incomplete or invalid, because Working Save remains draft-tolerant.

However:
- findings must expose subcircuit problems clearly
- invalid subcircuit references must not be hidden

### 12.2 Commit Snapshot
Commit Snapshot may contain SubcircuitNode only when:
- child references resolve
- mappings are valid
- child circuit validity passes
- blocking findings are absent

Approved snapshot truth must not contain unresolved subcircuit ambiguity.

## 13. Relationship to UI and Designer Layers

This savefile extension does not change the rule that:
- UI does not own structural truth
- Designer AI does not directly mutate committed truth

If Designer proposes SubcircuitNode insertion, it must still pass through:

    Intent -> Patch -> Precheck -> Preview -> Approval -> Commit

This document only defines how the approved or drafted result is stored.

## 14. First Official Example Binding

The first official example bound to this savefile extension is:

`Review Bundle`

Reason:
- simple parent-child mapping
- clear local child registry usage
- validates the `internal:` reference model
- validates explicit child outputs

## 15. Non-Goals for v0.1

This savefile extension does not include:
- inline child runtime state snapshots
- unrestricted arbitrary nested mutation
- automatic child flattening for storage convenience
- direct child trace embedding into parent structure
- child circuit as independent top-level runtime root
- registry/package distribution format for shared subcircuits

## 16. Final Rule

The savefile representation of subcircuits must increase composition power without weakening Nexa's node-centered structure.

Final statement:

Subcircuit support in `.nex` savefiles is expressed through `kind: "subcircuit"` parent nodes plus an optional local `subcircuits` registry, while preserving the rule that child circuits remain bounded, referenced, and wrapper-mediated.
