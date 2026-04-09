# Proposal Document Set Index

## Recommended save path
`docs/specs/meta/proposal_document_set_index.md`

## 1. Purpose

This document is the official index for the proposal set that has been adopted or partially adopted for Nexa.

Its purpose is to:
- organize all proposal directions that have been accepted for documentation
- distinguish already-documented items from not-yet-documented items
- prevent duplicate proposal handling
- provide one authoritative entry point for future implementation review

This is not a replacement for the underlying specs.
It is a routing and consolidation document.

## 2. Classification Rule

The proposals are organized into three groups:

1. Productization / beginner-surface proposals
2. Stage 1 engine-expansion proposals
3. Deferred platform / architecture-shift proposals

In addition, each proposal is marked as one of:

- documented
- documented indirectly
- documented here as pending design
- intentionally deferred

## 3. Productization / Beginner-Surface Proposal Set

### 3.1 Beginner shell compression
Status: documented

Primary spec:
- `docs/specs/ui/beginner_shell_compression_policy.md`

### 3.2 General user productization priority
Status: documented

Primary spec:
- `docs/specs/ui/general_user_productization_priority.md`

### 3.3 Beginner-facing return-use loop additions
Status: documented inside productization priority

Covered topics:
- circuit list / library surface
- beginner-facing result history
- onboarding continuity
- user feedback channel
- accessibility
- localization completeness

### 3.4 Trigger / delivery engine value for general users
Status: documented

Primary spec:
- `docs/specs/automation/automation_trigger_delivery_contract.md`

### 3.5 Execution streaming as separate but compatible engine contract
Status: documented

Primary spec:
- `docs/specs/execution/execution_streaming_contract.md`

### 3.6 Output destination as governed outbound delivery
Status: documented

Primary spec:
- `docs/specs/automation/output_destination_contract.md`

### 3.7 Input safety as pre-execution gate
Status: documented

Primary spec:
- `docs/specs/safety/input_safety_contract.md`

### 3.8 Usage quota as governance boundary
Status: documented

Primary spec:
- `docs/specs/governance/usage_quota_contract.md`

## 4. Stage 1 Engine-Expansion Proposal Set

### 4.1 Stage 1 engine contract bundle index
Status: documented

Primary spec:
- `docs/specs/engine/stage1_engine_contract_index.md`

### 4.2 Execution governance integration
Status: documented

Primary spec:
- `docs/specs/engine/execution_governance_integration_contract.md`

### 4.3 Shared reason code / status taxonomy
Status: documented

Primary spec:
- `docs/specs/engine/reason_code_status_taxonomy_contract.md`

## 5. Not-Yet-Documented Proposal Areas

The following proposals are documented in this bundle as pending design areas because they were identified but not yet turned into standalone canonical specs.

### 5.1 Batch execution
Status: documented here as pending design

Reason:
- useful platform-strengthening feature
- not Stage 1 general-user critical
- requires separate engine contract

### 5.2 Auto-evaluation node / quality automation
Status: documented here as pending design

Reason:
- high-value engine quality capability
- not first-success critical
- needs separate evaluation-layer contract

### 5.3 Regression alert automation
Status: documented here as pending design

Reason:
- regression detection exists conceptually
- automatic user-facing alert contract not yet fixed

## 6. Explicitly Deferred Proposal Areas

### 6.1 Conditional branch / loop nodes
Status: intentionally deferred

Reason:
- advanced automation capability
- conflicts with beginner-surface simplicity if introduced too early
- better treated as later architecture/platform expansion

### 6.2 Cross-run memory
Status: intentionally deferred

Reason:
- changes product semantics
- needs a separate memory contract
- not required for current general-user first-success priority

### 6.3 Interactive / conversational execution
Status: intentionally deferred

Reason:
- risks shifting Nexa from execution engine toward conversational agent system
- requires explicit architectural decision before documentation as committed scope

## 7. Recommended Reading Order

1. `beginner_shell_compression_policy.md`
2. `general_user_productization_priority.md`
3. `automation_trigger_delivery_contract.md`
4. `execution_streaming_contract.md`
5. `output_destination_contract.md`
6. `input_safety_contract.md`
7. `usage_quota_contract.md`
8. `stage1_engine_contract_index.md`
9. `execution_governance_integration_contract.md`
10. `reason_code_status_taxonomy_contract.md`
11. `engine_proposals_deferred_and_pending.md`
12. `proposal_implementation_sequence.md`

## 8. Final Statement

Once accepted, proposals must either:
- become canonical specs,
- become explicitly pending design documents,
- or become explicitly deferred items.

This index exists to keep that boundary clean.
