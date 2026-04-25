# Engine Proposals Deferred and Pending

## Recommended save path
`docs/specs/engine/engine_proposals_deferred_and_pending.md`

## 1. Purpose

This document records engine-expansion proposals that are not yet committed as immediate canonical implementation scope.

Its purpose is to:
- prevent those proposals from being lost
- distinguish pending platform-strengthening work from deliberately deferred architecture-shift work
- preserve reasoning about why each item is not currently in Stage 1 implementation scope

This document is not a commitment to immediate implementation.
It is a controlled holding document.

## 2. Classification

The proposals in this document are divided into:

1. Pending platform-strengthening proposals
2. Deferred architecture-shift proposals

## 3. Pending Platform-Strengthening Proposals

### 3.1 Batch Execution Contract

**Status**
Pending design

**Why it matters**
Batch execution supports one request driving many inputs in one bounded execution family.

Examples:
- analyze 100 reviews
- run the same circuit over multiple records
- compare repeated structured input sets

**Why it is not Stage 1**
Batch execution is useful, but it is not the main blocker for first-success general-user productization.
File/URL input, trigger automation, governed output delivery, safety, quota, and streaming are higher-value earlier moves.

**What it would likely require**
- batch-aware execution request model
- batch run grouping identity
- item-level vs batch-level result separation
- batch quota accounting
- batch trace compression / expansion rules

**Design constraint**
Batch execution must not redefine Node as the sole execution unit.

### 3.2 Auto-Evaluation / Evaluation Node Contract

**Status**
Pending design

**Why it matters**
Nexa becomes more trustworthy when outputs can be evaluated automatically under explicit quality logic.

Examples:
- quality check result before delivery
- compare candidate outputs
- reject low-confidence result and request retry path
- generate structured quality findings for downstream review

**Why it is not Stage 1**
It strengthens engine quality, but it is not as foundational as streaming, automation trigger/delivery, safety, quota, or governed outbound delivery for current productization.

**What it would likely require**
- evaluation node type or evaluation contract family
- structured evaluator result object
- machine-usable reason codes
- retry/re-route hooks
- compatibility with approval and delivery policy

**Design constraint**
Evaluation output must remain distinguishable from approval truth.
Evaluation is evidence, not authority.

### 3.3 Regression Alert Automation Contract

**Status**
Pending design

**Why it matters**
If Nexa can detect regression, it should eventually support explicit policy about how that regression becomes visible.

Examples:
- alert when quality dropped compared to previous run
- notify user when delivery output worsened materially
- open a review issue automatically on significant degradation

**Why it is not Stage 1**
Stage 1 must first establish trustworthy execution, delivery, safety, and quota semantics.
Regression alert automation is a higher-order platform-strengthening layer.

**What it would likely require**
- regression event contract
- alert policy contract
- threshold semantics
- recipient/destination mapping
- audit trail for auto-raised regression alerts

**Design constraint**
Regression detection and alerting must remain separate.
Detection does not imply mandatory notification.

## 4. Deferred Architecture-Shift Proposals

### 4.1 Conditional Branch / Loop Node Family

**Status**
Deferred

**Canonical documents**
- `docs/specs/engine/conditional_branch_loop_node_family.md`
- `docs/specs/engine/conditional_branch_node_deferred_contract.md`
- `docs/specs/engine/loop_node_deferred_contract.md`
- `docs/specs/engine/loop_streaming_output_deferred_contract.md`

**Why deferred**
This is powerful but materially increases control-flow complexity.
It belongs to later platform expansion, not current beginner/productization-first convergence.

**Current boundary**
Structural fan-out and dependency fan-in are allowed under `docs/specs/execution/circuit_graph_control_flow_contract.md`.
Explicit conditional branch and loop node support remains deferred.
Raw graph cycles remain invalid.

### 4.2 Dynamic Graph Mutation / Autonomous Graph Rewrite

**Status**
Deferred / currently prohibited

**Canonical document**
- `docs/specs/engine/dynamic_graph_mutation_deferred_contract.md`

**Why deferred**
Dynamic runtime graph mutation changes validation, scheduler, trace, replay, artifact lineage, and approval truth.
It must remain prohibited unless a future major architecture decision explicitly promotes it.

**Current boundary**
Structural changes must go through proposal, precheck, preview, approval, and commit.
They must not occur as hidden runtime mutation.

### 4.3 Cross-Run Memory Contract

**Status**
Deferred

**Canonical document**
- `docs/specs/engine/cross_run_memory_contract.md`

**Why deferred**
Cross-run memory is not just a feature.
It changes what a run means across time.

### 4.4 Interactive / Conversational Execution Contract

**Status**
Deferred

**Canonical document**
- `docs/specs/engine/interactive_conversational_execution_contract.md`

**Why deferred**
This is the clearest product-character shift proposal in this proposal set.

## 5. Final Statement

Not all good proposals should be normalized into immediate scope.

This document exists so that:
- valuable proposals are preserved,
- Stage 1 scope stays clean,
- and architecture-shift ideas remain deferred until intentionally reopened.
