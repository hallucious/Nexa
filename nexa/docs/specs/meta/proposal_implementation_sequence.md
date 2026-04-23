# Proposal Implementation Sequence

## Recommended save path
`docs/specs/meta/proposal_implementation_sequence.md`

## 1. Purpose

This document defines the recommended implementation sequence for the proposal set that has already been documented in Nexa.

Its purpose is to convert the proposal document set into an actionable sequencing guide for implementation planning, implementation prompting, and review.

This document is sequencing-oriented.
It does not replace any underlying contract.

## 2. Core Rule

Implementation order must follow dependency clarity, not proposal arrival order.

Official rule:

- earlier steps should reduce ambiguity for later steps
- governance/safety/identity layers should appear before feature acceleration layers
- subsystem integration should happen before UI simplification tries to summarize it
- later implementation must not force redefinition of earlier truth boundaries

## 3. Recommended Sequence

### Sequence 1 — Identity and lifecycle spine
Documents:
- `automation_trigger_delivery_contract.md`
- `stage1_engine_contract_index.md`
- `execution_governance_integration_contract.md`

### Sequence 2 — Runtime truth projection
Documents:
- `execution_streaming_contract.md`
- `reason_code_status_taxonomy_contract.md`

### Sequence 3 — Pre-launch governance
Documents:
- `input_safety_contract.md`
- `usage_quota_contract.md`

### Sequence 4 — Outbound result governance
Documents:
- `output_destination_contract.md`

### Sequence 5 — Beginner/productization enforcement
Documents:
- `beginner_shell_compression_policy.md`
- `general_user_productization_priority.md`

## 4. Recommended Review Gates

### After Sequence 1
- is one canonical lifecycle visible?
- are trigger, launch, execution, and delivery still distinguishable?
- is shared run identity stable?

### After Sequence 2
- are partial and final outputs still distinct?
- are reason codes subsystem-stable?
- can UI project runtime state without inventing it?

### After Sequence 3
- can unsafe input be blocked before launch?
- can quota block cleanly without masquerading as validation or run failure?
- are accounting and launch decisions structurally separable?

### After Sequence 4
- is outbound delivery explicit?
- is selected output/artifact explicit?
- can execution success remain separate from delivery success?

### After Sequence 5
- can beginner UI simplify without falsifying?
- can general-user loops be completed without exposing deep engine complexity?
- are return-use and inclusion surfaces still grounded in stable truth?

## 5. Relationship to Deferred/Pending Proposals

This sequence intentionally excludes:
- batch execution
- auto-evaluation node
- regression alert automation
- branch/loop nodes
- cross-run memory
- interactive execution

## 6. Final Statement

The proposal set should not be implemented in the order it was proposed.

It should be implemented in the order that produces the cleanest, most governable Nexa engine and the least rework later.
