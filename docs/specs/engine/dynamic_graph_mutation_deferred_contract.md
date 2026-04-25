# Dynamic Graph Mutation Deferred Contract v0.1

## Recommended save path
`docs/specs/engine/dynamic_graph_mutation_deferred_contract.md`

## 1. Status

Deferred / currently prohibited.

This document preserves the future design boundary for dynamic graph mutation and autonomous graph rewrite.
It does not authorize either behavior.

## 2. Purpose

This document defines the rule that runtime graph structure must not be mutated implicitly during execution.

It also records the minimum conditions that would have to be satisfied before any future dynamic graph mutation or autonomous graph rewrite is considered.

## 3. Core Decision

Current Nexa rule:

- runtime graph mutation is prohibited
- scheduler self-modification is prohibited
- autonomous graph rewrite is prohibited
- structure changes must go through explicit proposal, validation, preview, approval, and commit boundaries

## 4. Current Allowed Structural Change Path

The canonical structural change path remains:

    Intent
    -> Patch
    -> Precheck
    -> Preview
    -> Approval
    -> Commit

This path is design-time / commit-time.
It is not hidden runtime mutation.

## 5. Prohibited Current Behaviors

The following are prohibited in the current engine model:

- node adds a new node during execution
- node deletes an edge during execution
- plugin rewrites circuit structure during execution
- provider output directly mutates scheduler topology
- loop is implemented by adding edges dynamically
- branch is implemented by deleting unselected edges dynamically
- Designer AI silently commits structural changes
- autonomous agent rewrites the graph and reruns without approval

## 6. Future Mutation Design Requirements

If this area is ever reopened, any mutation mechanism must define:

- mutation scope
- allowed actor
- allowed time boundary
- patch record
- approval requirements
- validation before activation
- structural fingerprint transition
- trace linkage
- rollback / restore semantics
- replay semantics
- safety and quota implications

## 7. Between-Run vs During-Run Mutation

A future design must distinguish:

### 7.1 Between-run mutation

Potentially acceptable if approval-gated and commit-recorded.

This is essentially an enhanced patch/commit system.

### 7.2 During-run mutation

Much higher risk.

During-run mutation would affect replay, trace, scheduler, artifact lineage, and validation truth.
It must remain prohibited unless a future major architecture decision explicitly promotes it.

## 8. Autonomous Graph Rewrite

Autonomous graph rewrite is a stronger version of dynamic mutation.

It would require:

- explicit authority model
- proposal boundaries
- human approval or bounded policy approval
- rewrite diff
- validation gate
- rollback path
- audit record
- safety review
- replay compatibility decision

Current rule:

Autonomous graph rewrite is not permitted.

## 9. Validation Anchors

Existing and planned anchors:

- ENG-004 Dynamic Structure Mutation Declared/Detected
- NODE-005 Node Attempts Structural Control
- FLOW-003 Channel Encodes Control Logic

These rules should remain strict until a future mutation contract is explicitly promoted.

## 10. Final Statement

Dynamic graph mutation is not a convenience feature.
It changes the meaning of execution, validation, replay, and approval.

Therefore current Nexa must treat graph mutation as a proposal/commit action, not as hidden runtime behavior.
