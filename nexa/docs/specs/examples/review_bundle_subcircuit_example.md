# Review Bundle Subcircuit Example v0.1

## Recommended save path
`docs/specs/examples/review_bundle_subcircuit_example.md`

## 1. Purpose

This document defines the first official end-to-end example for `SubcircuitNode` in Nexa.

Its purpose is to lock the initial practical interpretation of SubcircuitNode with a concrete parent-child circuit example.

This example is not merely illustrative.
It is the official reference example for validating:

- parent-child boundary
- explicit input mapping
- explicit output binding
- local `internal:` child resolution
- child-circuit reuse semantics
- role allocation across multiple AI providers

## 2. Why Review Bundle Is the First Official Example

`Review Bundle` is the preferred first example because it is complex enough to justify hierarchical composition, but still simple enough to validate clearly.

It is especially suitable because it needs:

- one parent-level task
- one reusable child review bundle
- multiple internal review roles
- explicit synthesis
- clear parent-visible outputs

This makes it a good v0.1 example for SubcircuitNode.

## 3. High-Level Intent

The parent circuit generates an initial draft.
Then it passes that draft into a reusable child circuit called `review_bundle`.
The child circuit critiques, checks evidence, and synthesizes a reviewed result.
The parent circuit then continues using the bundled review output.

In short:

- parent generates draft
- child reviews draft
- parent uses reviewed result

## 4. Parent Circuit Shape

Canonical parent shape:

    Input
    -> Draft Generator
    -> Review Bundle (SubcircuitNode)
    -> Final Judge

The parent circuit sees `Review Bundle` as one node.
It does not directly schedule the child nodes.

## 5. Child Circuit Shape

Canonical child shape:

    Draft Critic
    Evidence Check
    -> Review Synthesizer

This child circuit is stored locally in the savefile `subcircuits` registry and referenced by:

    internal:review_bundle

## 6. Official Role Allocation

Preferred v0.1 provider role allocation:

- GPT: draft generation and final synthesis-friendly generation tasks
- Claude: critique and structured review
- Perplexity: evidence lookup / evidence check

Recommended role mapping in this example:

### Parent level
- `Draft Generator` -> GPT
- `Final Judge` -> Claude or GPT depending on policy

### Child level
- `Draft Critic` -> Claude
- `Evidence Check` -> Perplexity
- `Review Synthesizer` -> GPT

This distribution is preferred because the child bundle combines critique, external evidence, and synthesis in a way that maps well to the current multi-model strategy.

## 7. Parent-Level Input

Canonical parent input example:

    input.question = "Which market entry strategy is safer?"

Optional future parent input examples:
- target market
- budget context
- risk tolerance
- time horizon

For v0.1, one main question is enough.

## 8. Parent Node Definitions

### 8.1 Draft Generator
Role:
- produces the first decision draft

Expected parent-visible output:
- `node.draft_generator.output.result`

### 8.2 Review Bundle
Role:
- wraps the child `review_bundle` circuit

Node kind:
- `subcircuit`

Child reference:
- `internal:review_bundle`

### 8.3 Final Judge
Role:
- consumes the reviewed bundle result
- produces the final parent-level decision

Expected parent-visible output:
- `node.final_judge.output.result`

## 9. Canonical Parent SubcircuitNode Definition

Canonical parent wrapper definition:

    node_id: review_bundle_stage
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

## 10. Canonical Child Circuit Definition

Canonical child circuit intent:

### 10.1 Draft Critic
Reads:
- child input question
- child input draft

Produces:
- critique findings
- weaknesses
- concerns
- alternative framing hints

### 10.2 Evidence Check
Reads:
- child input question
- child input draft

Produces:
- evidence summary
- factual support / contradiction signals
- evidence gaps
- uncertainty markers

### 10.3 Review Synthesizer
Reads:
- Draft Critic outputs
- Evidence Check outputs

Produces:
- reviewed result
- confidence
- reasoning summary

## 11. Canonical Child Outputs

The child circuit must explicitly declare outputs.

Minimum official outputs:

    result
    confidence
    reasoning_summary

Optional future outputs:
- issues_found
- evidence_summary
- unresolved_questions

For v0.1, the minimum official outputs are enough.

## 12. Parent-Child Mapping Semantics

### 12.1 Parent -> child
Allowed only through explicit `input_mapping`.

This example uses:

    question <- input.question
    draft <- node.draft_generator.output.result

### 12.2 Child -> parent
Allowed only through explicit `output_binding`.

This example uses:

    result <- child.output.result
    confidence <- child.output.confidence
    reasoning_summary <- child.output.reasoning_summary

### 12.3 Forbidden
This example forbids:
- direct child mutation of parent working context
- direct parent reads of child internal node state
- implicit export of all child outputs
- flattening child internals into parent-local execution truth

## 13. Minimal Savefile Sketch

Canonical simplified savefile sketch:

    meta:
      storage_role: working_save

    circuit:
      nodes:
        - draft_generator
        - review_bundle_stage
        - final_judge
      edges:
        - draft_generator -> review_bundle_stage
        - review_bundle_stage -> final_judge

    subcircuits:
      review_bundle:
        nodes:
          - draft_critic
          - evidence_check
          - review_synthesizer
        edges:
          - draft_critic -> review_synthesizer
          - evidence_check -> review_synthesizer
        outputs:
          - result
          - confidence
          - reasoning_summary

## 14. Expected Runtime Behavior

Expected runtime sequence:

1. Parent runtime executes `Draft Generator`
2. Parent runtime reaches `Review Bundle`
3. Parent runtime resolves input mappings
4. Child runtime is created for `review_bundle`
5. Child runtime executes `Draft Critic`
6. Child runtime executes `Evidence Check`
7. Child runtime executes `Review Synthesizer`
8. Child runtime emits child outputs
9. Parent runtime binds child outputs to parent node-level outputs
10. Parent runtime continues to `Final Judge`

The parent scheduler must never directly treat child nodes as parent-local nodes.

## 15. Expected Parent-Visible Outputs

After the SubcircuitNode finishes, the parent should be able to read:

    node.review_bundle_stage.output.result
    node.review_bundle_stage.output.confidence
    node.review_bundle_stage.output.reasoning_summary

These are the parent-level outputs of the wrapper node.

## 16. Expected Trace Behavior

Expected parent trace summary:
- subcircuit node started
- child run started
- child run finished
- subcircuit node finished
- child trace linkage

Expected child trace:
- child-owned detailed execution history
- separate from parent event stream
- linked, not flattened

## 17. Expected Artifact Behavior

If child internals create artifacts:
- artifacts remain child-owned
- parent may receive refs or summaries
- append-only meaning remains intact

This example does not require heavy artifact behavior for v0.1, but it must remain compatible with it.

## 18. Validation Expectations

This example must validate all of the following:

1. `kind = "subcircuit"` is recognized
2. `execution.subcircuit` block exists
3. `child_circuit_ref = internal:review_bundle` resolves
4. `input_mapping` paths are valid
5. `output_binding` targets are valid
6. child outputs exist
7. child circuit is structurally valid
8. no recursive self-reference exists
9. no cycle reference exists
10. child depth policy is respected

## 19. Why This Example Matters

This example is important because it demonstrates the first real payoff of SubcircuitNode:

- reusable internal circuit composition
- multi-model role specialization
- bounded hierarchical execution
- no violation of the Node-as-execution-unit rule

Without an example like this, SubcircuitNode would remain a purely abstract feature.

## 20. Non-Goals of This Example

This example does not attempt to demonstrate:
- unrestricted recursive composition
- dynamic child mutation
- cross-savefile registry distribution
- deep artifact orchestration
- UI-specific graph rendering
- Designer-driven automatic insertion

It is a focused runtime/storage/contract example.

## 21. Final Rule

`Review Bundle` is the first official validation example for SubcircuitNode v0.1.

Final statement:

The Review Bundle example demonstrates how Nexa can support reusable hierarchical circuit composition through a SubcircuitNode wrapper while preserving explicit boundaries, mapping-based exchange, and Node-centered runtime semantics.
